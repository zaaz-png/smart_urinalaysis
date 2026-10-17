"""PDF reports (ReportLab) and CSV import/export."""
import csv
from datetime import datetime

import database as db
import validation as V

DISCLAIMER = ("A flagged result is not a diagnosis. Results must be reviewed by a qualified "
              "professional. Records marked 'Synthetic' are fictional demonstration data.")


def _reference_text(name, rules):
    spec = V.BY_NAME[name]
    if spec["kind"] == "numeric":
        low, high = rules[name]
        fmt = "{:.3f}" if name == "Specific gravity" else "{:g}"
        return f"{fmt.format(low)} – {fmt.format(high)}"
    return spec["options"][0]


def generate_test_report(test_id, path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise RuntimeError("ReportLab is not installed. Run: pip install reportlab")

    head, results = db.test_detail(test_id)
    if head is None:
        raise ValueError("Test not found.")
    rules = db.get_rules()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=f"Urinalysis report {test_id}")

    info = Table([
        ["Patient ID", head["patient_code"], "Test ID", str(head["test_id"])],
        ["Name", head["name"], "Test time", head["tested_at"]],
        ["Age / Sex", f"{head['age']} / {head['sex'] or '—'}", "Source", head["source"]],
        ["Review status", head["review_status"], "Report created", datetime.now().strftime(db.TIME_FMT)],
    ], colWidths=[28 * mm, 52 * mm, 30 * mm, 52 * mm])
    info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey)]))

    data = [["Parameter", "Result", "Unit", "Reference", "Flag"]]
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263238")),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
             ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for i, r in enumerate(results, start=1):
        data.append([r["analyte"], r["value"], r["unit"] or "—", _reference_text(r["analyte"], rules), r["flag"]])
        if r["flag"] != "Normal":
            style += [("TEXTCOLOR", (4, i), (4, i), colors.HexColor(V.FLAG_COLORS[r["flag"]])),
                      ("FONTNAME", (4, i), (4, i), "Helvetica-Bold"), ("FONTNAME", (1, i), (1, i), "Helvetica-Bold")]
    table = Table(data, colWidths=[48 * mm, 30 * mm, 24 * mm, 40 * mm, 30 * mm])
    table.setStyle(TableStyle(style))

    n_flag = sum(r["flag"] != "Normal" for r in results)
    story = [Paragraph("Urinalysis Report", styles["Title"]), info, Spacer(1, 8 * mm), table, Spacer(1, 5 * mm),
             Paragraph(f"<b>{n_flag}</b> of {len(results)} parameters outside the reference rules.", styles["Normal"])]
    if head["notes"]:
        story += [Spacer(1, 3 * mm), Paragraph(f"<b>Notes:</b> {head['notes']}", styles["Normal"])]
    story += [Spacer(1, 10 * mm), Paragraph(f"<i>{DISCLAIMER}</i>", styles["Italic"])]
    doc.build(story)


# --------------------------------------------------------------------- CSV
CSV_FIELDS = ["patient_code", "name", "age", "sex", "tested_at", "source", "review_status"] + V.NAMES


def export_csv(path):
    rows = db.export_rows()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def _norm(h):
    return h.strip().lower().replace("_", " ")


def _parse_time(text):
    text = (text or "").strip()
    for fmt in (db.TIME_FMT, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime(db.TIME_FMT)
        except ValueError:
            pass
    raise ValueError(f"unrecognised date/time '{text}' (use YYYY-MM-DD HH:MM)")


def import_csv(path, source="Imported"):
    """Import tests from a wide CSV (same columns as export). Returns (imported, skipped, errors)."""
    imported, skipped, errors = 0, 0, []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = {_norm(h): h for h in (reader.fieldnames or [])}
        missing = [c for c in ["patient code", "tested at"] + [n.lower() for n in V.NAMES] if c not in cols]
        if missing:
            raise ValueError("Missing CSV columns: " + ", ".join(missing))
        get = lambda row, key: (row.get(cols[key]) or "").strip() if key in cols else ""
        for line, row in enumerate(reader, start=2):
            try:
                code = get(row, "patient code")
                when = _parse_time(get(row, "tested at"))
                values = {n: get(row, n.lower()) for n in V.NAMES}
                for n in V.NAMES:                       # validate before touching the database
                    _, err = V.validate_value(n, values[n])
                    if err:
                        raise ValueError(err)
                patient = db.find_patient_by_code(code)
                if patient:
                    pid = patient["patient_id"]
                else:
                    pid = db.add_patient(code, get(row, "name") or "Imported patient",
                                         get(row, "age"), get(row, "sex") or None)
                db.add_test(pid, values, source=source, tested_at=when)
                imported += 1
            except ValueError as e:
                skipped += 1
                errors.append(f"Row {line}: {e}")
    return imported, skipped, errors
