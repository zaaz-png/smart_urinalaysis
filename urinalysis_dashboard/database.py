"""SQLite layer: schema, queries and transactional writes."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import validation as V

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "urinalysis.db")
SOURCES = ("Synthetic", "Imported", "Manual", "Device")
REVIEW_STATES = ("Not Required", "Pending Review", "Reviewed")
TIME_FMT = "%Y-%m-%d %H:%M"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_code  TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    age           INTEGER NOT NULL CHECK (age BETWEEN 0 AND 120),
    sex           TEXT CHECK (sex IN ('F', 'M', 'Other') OR sex IS NULL),
    registered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tests (
    test_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    tested_at     TEXT NOT NULL,
    source        TEXT NOT NULL CHECK (source IN ('Synthetic','Imported','Manual','Device')),
    review_status TEXT NOT NULL DEFAULT 'Not Required'
                  CHECK (review_status IN ('Not Required','Pending Review','Reviewed')),
    notes         TEXT
);
CREATE TABLE IF NOT EXISTS test_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id   INTEGER NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
    analyte   TEXT NOT NULL,
    value     TEXT NOT NULL,
    unit      TEXT,
    flag      TEXT NOT NULL CHECK (flag IN ('Normal','Borderline','Abnormal')),
    UNIQUE (test_id, analyte)
);
CREATE TABLE IF NOT EXISTS audit_log (
    log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at TEXT NOT NULL,
    action    TEXT NOT NULL,
    entity    TEXT,
    entity_id INTEGER,
    details   TEXT
);
CREATE TABLE IF NOT EXISTS reference_rules (
    analyte TEXT PRIMARY KEY,
    low     REAL NOT NULL,
    high    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tests_patient ON tests(patient_id, tested_at);
"""

# Per-test counts of flagged results, reused by several queries.
_FLAG_COUNTS = """
    (SELECT COUNT(*) FROM test_results r WHERE r.test_id = t.test_id AND r.flag = 'Abnormal')   AS n_abnormal,
    (SELECT COUNT(*) FROM test_results r WHERE r.test_id = t.test_id AND r.flag = 'Borderline') AS n_borderline
"""


def now():
    return datetime.now().strftime(TIME_FMT)


@contextmanager
def tx():
    """Connection that commits on success and rolls back on any error."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with tx() as con:
        con.executescript(SCHEMA)


def _audit(con, action, entity, entity_id, details=""):
    con.execute(
        "INSERT INTO audit_log (logged_at, action, entity, entity_id, details) VALUES (?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, entity, entity_id, details))


# ----------------------------------------------------------------- patients
def next_patient_code():
    with tx() as con:
        n = con.execute("SELECT COALESCE(MAX(patient_id), 0) FROM patients").fetchone()[0] + 1
        while con.execute("SELECT 1 FROM patients WHERE patient_code = ?", (f"P{n:04d}",)).fetchone():
            n += 1
    return f"P{n:04d}"


def _clean_patient(code, name, age, sex):
    code, name = (code or "").strip(), (name or "").strip()
    if not code:
        raise ValueError("Patient ID is required.")
    if not name:
        raise ValueError("Name is required.")
    try:
        age = int(str(age).strip())
    except ValueError:
        raise ValueError("Age must be a whole number.")
    if not 0 <= age <= 120:
        raise ValueError("Age must be between 0 and 120.")
    sex = (sex or "").strip() or None
    if sex not in (None, "F", "M", "Other"):
        raise ValueError("Sex must be F, M or Other (or left blank).")
    return code, name, age, sex


def add_patient(code, name, age, sex=None):
    code, name, age, sex = _clean_patient(code, name, age, sex)
    try:
        with tx() as con:
            cur = con.execute(
                "INSERT INTO patients (patient_code, name, age, sex, registered_at) VALUES (?,?,?,?,?)",
                (code, name, age, sex, now()))
            _audit(con, "CREATE", "patient", cur.lastrowid, f"{code} {name}")
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Patient ID '{code}' already exists.")


def update_patient(patient_id, code, name, age, sex=None):
    code, name, age, sex = _clean_patient(code, name, age, sex)
    try:
        with tx() as con:
            con.execute("UPDATE patients SET patient_code=?, name=?, age=?, sex=? WHERE patient_id=?",
                        (code, name, age, sex, patient_id))
            _audit(con, "UPDATE", "patient", patient_id, f"{code} {name}, age {age}, sex {sex}")
    except sqlite3.IntegrityError:
        raise ValueError(f"Patient ID '{code}' already exists.")


def list_patients(search=""):
    like = f"%{search.strip()}%"
    with tx() as con:
        return con.execute(
            """SELECT p.*, (SELECT COUNT(*) FROM tests t WHERE t.patient_id = p.patient_id) AS n_tests
               FROM patients p WHERE p.name LIKE ? OR p.patient_code LIKE ? ORDER BY p.name""",
            (like, like)).fetchall()


def find_patient_by_code(code):
    with tx() as con:
        return con.execute("SELECT * FROM patients WHERE patient_code = ?", (code.strip(),)).fetchone()


def patient_choices():
    with tx() as con:
        rows = con.execute("SELECT patient_id, patient_code, name FROM patients ORDER BY name").fetchall()
    return [(r["patient_id"], f"{r['patient_code']} – {r['name']}") for r in rows]


# -------------------------------------------------------------------- rules
def _rules(con):
    rules = dict(V.DEFAULT_RULES)
    for r in con.execute("SELECT analyte, low, high FROM reference_rules"):
        rules[r["analyte"]] = (r["low"], r["high"])
    return rules


def get_rules():
    with tx() as con:
        return _rules(con)


def set_rule(analyte, low, high):
    if analyte not in V.NUMERIC_NAMES:
        raise ValueError(f"{analyte} has no numeric range.")
    if not low < high:
        raise ValueError(f"{analyte}: the lower limit must be below the upper limit.")
    with tx() as con:
        con.execute("INSERT INTO reference_rules (analyte, low, high) VALUES (?,?,?) "
                    "ON CONFLICT(analyte) DO UPDATE SET low=excluded.low, high=excluded.high",
                    (analyte, low, high))
        _audit(con, "RULE", "reference_rules", None, f"{analyte}: {low} to {high}")


def reset_rules():
    with tx() as con:
        con.execute("DELETE FROM reference_rules")
        _audit(con, "RULE", "reference_rules", None, "reset to defaults")


def reflag_all():
    """Re-apply the current rules to stored numeric results and sync review status."""
    with tx() as con:
        rules = _rules(con)
        marks = ",".join("?" * len(V.NUMERIC_NAMES))
        for r in con.execute(f"SELECT result_id, analyte, value FROM test_results WHERE analyte IN ({marks})",
                             V.NUMERIC_NAMES).fetchall():
            con.execute("UPDATE test_results SET flag=? WHERE result_id=?",
                        (V.flag_result(r["analyte"], r["value"], rules), r["result_id"]))
        con.execute("""UPDATE tests SET review_status='Pending Review' WHERE review_status='Not Required'
                       AND EXISTS (SELECT 1 FROM test_results r WHERE r.test_id=tests.test_id AND r.flag<>'Normal')""")
        con.execute("""UPDATE tests SET review_status='Not Required' WHERE review_status='Pending Review'
                       AND NOT EXISTS (SELECT 1 FROM test_results r WHERE r.test_id=tests.test_id AND r.flag<>'Normal')""")
        _audit(con, "REFLAG", "test_results", None, "flags recomputed after rule change")


# -------------------------------------------------------------------- tests
def add_test(patient_id, values, source="Manual", notes="", tested_at=None):
    """Validate, flag and store one complete ten-parameter test in a single transaction."""
    if source not in SOURCES:
        raise ValueError(f"Source must be one of {', '.join(SOURCES)}.")
    clean, errors = {}, []
    for name in V.NAMES:
        value, err = V.validate_value(name, values.get(name))
        if err:
            errors.append(err)
        else:
            clean[name] = value
    if errors:
        raise ValueError("\n".join(errors))
    tested_at = tested_at or now()
    with tx() as con:
        rules = _rules(con)
        flags = {n: V.flag_result(n, clean[n], rules) for n in V.NAMES}
        status = "Pending Review" if any(f != "Normal" for f in flags.values()) else "Not Required"
        cur = con.execute(
            "INSERT INTO tests (patient_id, tested_at, source, review_status, notes) VALUES (?,?,?,?,?)",
            (patient_id, tested_at, source, status, notes or ""))
        test_id = cur.lastrowid
        con.executemany(
            "INSERT INTO test_results (test_id, analyte, value, unit, flag) VALUES (?,?,?,?,?)",
            [(test_id, n, clean[n], V.BY_NAME[n]["unit"], flags[n]) for n in V.NAMES])
        _audit(con, "CREATE", "test", test_id, f"patient {patient_id}, source {source}, status {status}")
    return test_id


def set_review(test_id, status):
    if status not in REVIEW_STATES:
        raise ValueError("Unknown review status.")
    with tx() as con:
        con.execute("UPDATE tests SET review_status=? WHERE test_id=?", (status, test_id))
        _audit(con, "REVIEW", "test", test_id, f"status set to {status}")


def tests_for_patient(patient_id):
    with tx() as con:
        return con.execute(f"SELECT t.*, {_FLAG_COUNTS} FROM tests t WHERE t.patient_id=? "
                           "ORDER BY t.tested_at DESC, t.test_id DESC", (patient_id,)).fetchall()


def recent_tests(limit=15):
    with tx() as con:
        return con.execute(
            f"""SELECT t.*, p.patient_code, p.name, {_FLAG_COUNTS}
                FROM tests t JOIN patients p ON p.patient_id = t.patient_id
                ORDER BY t.tested_at DESC, t.test_id DESC LIMIT ?""", (limit,)).fetchall()


def test_detail(test_id):
    """Return (test+patient row as dict, [result dicts in standard analyte order])."""
    with tx() as con:
        head = con.execute(
            """SELECT t.*, p.patient_code, p.name, p.age, p.sex
               FROM tests t JOIN patients p ON p.patient_id = t.patient_id WHERE t.test_id=?""",
            (test_id,)).fetchone()
        rows = con.execute("SELECT * FROM test_results WHERE test_id=?", (test_id,)).fetchall()
    results = sorted((dict(r) for r in rows), key=lambda r: V.NAMES.index(r["analyte"]))
    return (dict(head) if head else None), results


def analyte_history(patient_id, analyte):
    with tx() as con:
        return con.execute(
            """SELECT t.tested_at, r.value, r.flag FROM tests t
               JOIN test_results r ON r.test_id = t.test_id
               WHERE t.patient_id=? AND r.analyte=? ORDER BY t.tested_at""",
            (patient_id, analyte)).fetchall()


def stats():
    with tx() as con:
        q = lambda sql: con.execute(sql).fetchone()[0]
        return {
            "patients": q("SELECT COUNT(*) FROM patients"),
            "tests": q("SELECT COUNT(*) FROM tests"),
            "flagged": q("SELECT COUNT(*) FROM tests t WHERE EXISTS "
                         "(SELECT 1 FROM test_results r WHERE r.test_id=t.test_id AND r.flag<>'Normal')"),
            "pending": q("SELECT COUNT(*) FROM tests WHERE review_status='Pending Review'"),
        }


def export_rows():
    """One dict per test with patient fields, analyte values and review status (for CSV)."""
    with tx() as con:
        tests = con.execute(
            """SELECT t.test_id, p.patient_code, p.name, p.age, p.sex, t.tested_at, t.source, t.review_status
               FROM tests t JOIN patients p ON p.patient_id=t.patient_id ORDER BY t.tested_at""").fetchall()
        values = {}
        for r in con.execute("SELECT test_id, analyte, value FROM test_results"):
            values.setdefault(r["test_id"], {})[r["analyte"]] = r["value"]
    return [{**dict(t), **values.get(t["test_id"], {})} for t in tests]
