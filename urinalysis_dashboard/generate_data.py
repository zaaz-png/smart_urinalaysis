"""Synthetic data generator: fictional patients with realistic-looking trends.

Usage:  python generate_data.py [--patients 25] [--seed 42] [--reset]
Every record is stored with source = 'Synthetic'. Not for clinical conclusions.
"""
import argparse
import os
import random
from datetime import datetime, timedelta

import database as db
import validation as V

FIRST = ["Amara", "Liam", "Sofia", "Noah", "Chidi", "Mei", "Omar", "Elena", "Kofi", "Priya",
         "Lucas", "Fatima", "Daniel", "Aisha", "Tomas", "Grace", "Yusuf", "Hana", "Marco", "Zainab"]
LAST = ["Okafor", "Silva", "Nguyen", "Khan", "Mensah", "Rossi", "Haddad", "Petrov", "Adeyemi",
        "Tanaka", "Moreau", "Singh", "Costa", "Bello", "Ivanov", "Cohen", "Mwangi", "Lopez"]
PROFILES = ["healthy"] * 8 + ["diabetic", "uti", "kidney", "dehydrated"]


def _clamp(x, name):
    spec = V.BY_NAME[name]
    return min(max(x, spec["min"]), spec["max"])


def _cat(name, p, s=0.3):
    """Categorical result: 'Negative' with probability 1-p, else a heavier-tailed positive grade."""
    opts = V.BY_NAME[name]["options"]
    if random.random() > p:
        return opts[0]
    rest = opts[1:]
    return random.choices(rest, [(0.55 + 0.4 * s) ** i for i in range(len(rest))])[0]


def sample(profile, t):
    """One test's raw values. t in [0, 1] is progress through the patient's history."""
    v = {
        "Glucose": _cat("Glucose", 0.03), "Protein": _cat("Protein", 0.05),
        "pH": _clamp(random.gauss(6.3, 0.6), "pH"), "Ketones": _cat("Ketones", 0.03),
        "Blood": _cat("Blood", 0.04), "Bilirubin": _cat("Bilirubin", 0.02),
        "Urobilinogen": _clamp(random.gauss(0.6, 0.25), "Urobilinogen"),
        "Nitrite": "Positive" if random.random() < 0.02 else "Negative",
        "Leucocytes": _cat("Leucocytes", 0.05),
        "Specific gravity": _clamp(random.gauss(1.018, 0.006), "Specific gravity"),
    }
    if profile == "diabetic":
        v["Glucose"] = _cat("Glucose", 0.35 + 0.55 * t, t)
        v["Ketones"] = _cat("Ketones", 0.1 + 0.3 * t, t)
        v["Protein"] = _cat("Protein", 0.15 + 0.2 * t)
    elif profile == "uti":
        v["Nitrite"] = "Positive" if random.random() < 0.6 else "Negative"
        v["Leucocytes"] = _cat("Leucocytes", 0.85, 0.6)
        v["Blood"] = _cat("Blood", 0.4)
        v["Protein"] = _cat("Protein", 0.3)
        v["pH"] = _clamp(random.gauss(7.3, 0.5), "pH")
    elif profile == "kidney":
        v["Protein"] = _cat("Protein", 0.5 + 0.4 * t, 0.5 + 0.4 * t)
        v["Blood"] = _cat("Blood", 0.5)
        v["Specific gravity"] = _clamp(random.gauss(1.010, 0.004), "Specific gravity")
    elif profile == "dehydrated":
        v["Specific gravity"] = _clamp(random.gauss(1.029, 0.004), "Specific gravity")
        v["Ketones"] = _cat("Ketones", 0.3)
        v["Bilirubin"] = _cat("Bilirubin", 0.15)
        v["Urobilinogen"] = _clamp(random.gauss(1.1, 0.4), "Urobilinogen")
    return v


def generate(n_patients=25, seed=42):
    random.seed(seed)
    db.init_db()
    n_tests = 0
    for _ in range(n_patients):
        profile = random.choice(PROFILES)
        name = f"{random.choice(FIRST)} {random.choice(LAST)}"
        pid = db.add_patient(db.next_patient_code(), name, random.randint(18, 85),
                             random.choice(["F", "M", "Other"] if random.random() < 0.03 else ["F", "M"]))
        k = random.randint(3, 10)
        days = sorted(random.sample(range(1, 365), k), reverse=True)
        for i, d in enumerate(days):
            when = datetime.now() - timedelta(days=d, hours=random.randint(0, 8), minutes=random.randint(0, 59))
            values = sample(profile, i / max(k - 1, 1))
            tid = db.add_test(pid, values, source="Synthetic", tested_at=when.strftime(db.TIME_FMT),
                              notes=f"Synthetic profile: {profile}")
            detail, _ = db.test_detail(tid)
            if detail["review_status"] == "Pending Review" and d > 60:
                db.set_review(tid, "Reviewed")   # older flagged tests have been looked at
            n_tests += 1
    return n_patients, n_tests


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patients", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reset", action="store_true", help="delete the existing database first")
    args = ap.parse_args()
    if args.reset and os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    p, t = generate(args.patients, args.seed)
    print(f"Created {p} synthetic patients and {t} tests in {db.DB_PATH}")
