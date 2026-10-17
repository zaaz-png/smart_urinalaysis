# Smart Urinalysis Monitoring Dashboard

Python + Tkinter + SQLite3 (+ Matplotlib, ReportLab). Tkinter ships with Python
(on Debian/Ubuntu: `sudo apt install python3-tk`).

    pip install -r requirements.txt
    python generate_data.py --reset      # optional: 25 synthetic patients (CLI)
    python main.py                       # the app offers demo data if the DB is empty

Files: main.py (window, dashboard, reference-range dialog), database.py (schema, queries),
validation.py (analytes, validation, flag rules), patients.py, test_entry.py,
analytics.py (history + charts), reports.py (PDF, CSV), generate_data.py.

CSV import needs columns: patient_code, tested_at, and the ten parameters
(name, age, sex needed only for new patients). Use an export as a template.
Flags are not a diagnosis; Synthetic records are fictional.
