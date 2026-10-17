"""Analyte definitions, input validation and result flagging (no database access)."""

NEG_SCALE = ["Negative", "Trace", "+", "++", "+++"]

ANALYTES = [
    {"name": "Glucose", "kind": "categorical", "unit": "",
     "options": ["Negative", "Trace", "+", "++", "+++", "++++"]},
    {"name": "Protein", "kind": "categorical", "unit": "", "options": NEG_SCALE},
    {"name": "pH", "kind": "numeric", "unit": "", "min": 4.5, "max": 9.0},
    {"name": "Ketones", "kind": "categorical", "unit": "", "options": NEG_SCALE},
    {"name": "Blood", "kind": "categorical", "unit": "", "options": NEG_SCALE},
    {"name": "Bilirubin", "kind": "categorical", "unit": "",
     "options": ["Negative", "+", "++", "+++"]},
    {"name": "Urobilinogen", "kind": "numeric", "unit": "mg/dL", "min": 0.0, "max": 12.0},
    {"name": "Nitrite", "kind": "categorical", "unit": "", "options": ["Negative", "Positive"]},
    {"name": "Leucocytes", "kind": "categorical", "unit": "", "options": NEG_SCALE},
    {"name": "Specific gravity", "kind": "numeric", "unit": "", "min": 1.000, "max": 1.040},
]

BY_NAME = {a["name"]: a for a in ANALYTES}
NAMES = [a["name"] for a in ANALYTES]
NUMERIC_NAMES = [a["name"] for a in ANALYTES if a["kind"] == "numeric"]

# Default reference intervals for the numeric analytes (editable in the app).
DEFAULT_RULES = {
    "pH": (5.0, 8.0),
    "Urobilinogen": (0.2, 1.0),
    "Specific gravity": (1.005, 1.030),
}

FLAG_COLORS = {"Normal": "#2e7d32", "Borderline": "#ef6c00", "Abnormal": "#c62828"}
FLAG_BG = {"Borderline": "#fff3e0", "Abnormal": "#fdecea"}


def validate_value(analyte, raw):
    """Return (clean_value, error). Exactly one of the two is None."""
    spec = BY_NAME[analyte]
    raw = "" if raw is None else str(raw).strip()
    if not raw:
        return None, f"{analyte}: a value is required."
    if spec["kind"] == "numeric":
        try:
            num = float(raw)
        except ValueError:
            return None, f"{analyte}: '{raw}' is not a number."
        if not spec["min"] <= num <= spec["max"]:
            return None, f"{analyte}: must be between {spec['min']} and {spec['max']}."
        return (f"{num:.3f}" if analyte == "Specific gravity" else f"{num:g}"), None
    lookup = {o.lower(): o for o in spec["options"]}
    if raw.lower() not in lookup:
        return None, f"{analyte}: choose one of {', '.join(spec['options'])}."
    return lookup[raw.lower()], None


def flag_result(analyte, value, rules=None):
    """Return 'Normal', 'Borderline' or 'Abnormal' for a validated value."""
    spec = BY_NAME[analyte]
    if spec["kind"] == "numeric":
        low, high = {**DEFAULT_RULES, **(rules or {})}[analyte]
        return "Normal" if low <= float(value) <= high else "Abnormal"
    opts = spec["options"]
    i = opts.index(value)
    if i == 0:
        return "Normal"
    if "Trace" in opts and i == opts.index("Trace"):
        return "Borderline"
    return "Abnormal"


def grade(analyte, value):
    """Numeric position of a result, used for charting."""
    spec = BY_NAME[analyte]
    if spec["kind"] == "numeric":
        return float(value)
    return spec["options"].index(value)
