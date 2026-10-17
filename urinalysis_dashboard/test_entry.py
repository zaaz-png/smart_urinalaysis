"""Test-entry tab: record all ten urine parameters for a patient."""
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import database as db
import reports
import validation as V


class TestEntryTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=14)
        self.app = app
        self.patient_ids = {}

        head = ttk.Frame(self)
        head.pack(fill="x")
        ttk.Label(head, text="Patient").grid(row=0, column=0, sticky="w")
        self.patient_var = tk.StringVar()
        self.patient_box = ttk.Combobox(head, textvariable=self.patient_var, state="readonly", width=34)
        self.patient_box.grid(row=0, column=1, padx=(8, 24))
        ttk.Label(head, text="Source").grid(row=0, column=2, sticky="w")
        self.source_var = tk.StringVar(value="Manual")
        ttk.Combobox(head, textvariable=self.source_var, values=["Manual", "Device"],
                     state="readonly", width=10).grid(row=0, column=3, padx=(8, 24))
        ttk.Label(head, text="Test time").grid(row=0, column=4, sticky="w")
        self.time_var = tk.StringVar(value=db.now())
        ttk.Entry(head, textvariable=self.time_var, width=17).grid(row=0, column=5, padx=8)

        grid = ttk.LabelFrame(self, text="Urine strip parameters (all ten required)", padding=12)
        grid.pack(fill="x", pady=14)
        self.vars = {}
        for i, spec in enumerate(V.ANALYTES):
            r, c = i % 5, (i // 5) * 4
            ttk.Label(grid, text=spec["name"], width=16).grid(row=r, column=c, sticky="w", pady=5)
            var = tk.StringVar()
            self.vars[spec["name"]] = var
            if spec["kind"] == "categorical":
                w = ttk.Combobox(grid, textvariable=var, values=spec["options"], state="readonly", width=12)
                hint = ""
            else:
                w = ttk.Entry(grid, textvariable=var, width=14)
                hint = f"{spec['unit']}  ({spec['min']:g}–{spec['max']:g})".strip()
            w.grid(row=r, column=c + 1, padx=(0, 6))
            ttk.Label(grid, text=hint, foreground="#666").grid(row=r, column=c + 2, sticky="w", padx=(0, 30))

        notes = ttk.Frame(self)
        notes.pack(fill="x")
        ttk.Label(notes, text="Notes").pack(side="left")
        self.notes_var = tk.StringVar()
        ttk.Entry(notes, textvariable=self.notes_var).pack(side="left", fill="x", expand=True, padx=8)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=14)
        ttk.Button(btns, text="Save test", command=self.save).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear).pack(side="left", padx=8)

    def refresh(self):
        choices = db.patient_choices()
        self.patient_ids = {label: pid for pid, label in choices}
        self.patient_box["values"] = [label for _, label in choices]

    def select_patient(self, patient_id):
        self.refresh()
        for label, pid in self.patient_ids.items():
            if pid == patient_id:
                self.patient_var.set(label)

    def clear(self):
        for v in self.vars.values():
            v.set("")
        self.notes_var.set("")
        self.time_var.set(db.now())

    def save(self):
        pid = self.patient_ids.get(self.patient_var.get())
        if pid is None:
            messagebox.showerror("Cannot save test", "Select a patient first.")
            return
        try:
            when = datetime.strptime(self.time_var.get().strip(), db.TIME_FMT).strftime(db.TIME_FMT)
        except ValueError:
            messagebox.showerror("Cannot save test", "Test time must look like 2026-10-17 14:30.")
            return
        values = {k: v.get() for k, v in self.vars.items()}
        try:
            test_id = db.add_test(pid, values, self.source_var.get(), self.notes_var.get(), when)
        except ValueError as e:
            messagebox.showerror("Check the entered values", str(e))
            return
        _, results = db.test_detail(test_id)
        flagged = [f"{r['analyte']}: {r['value']} ({r['flag']})" for r in results if r["flag"] != "Normal"]
        msg = "Test saved.\n\n" + ("Flagged for review:\n" + "\n".join(flagged) if flagged
                                   else "All results are within the reference rules.")
        self.clear()
        self.app.refresh_all()
        if messagebox.askyesno("Test saved", msg + "\n\nCreate a PDF report now?"):
            path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"urinalysis_{test_id}.pdf",
                                                filetypes=[("PDF", "*.pdf")])
            if path:
                try:
                    reports.generate_test_report(test_id, path)
                except Exception as e:
                    messagebox.showerror("Report failed", str(e))
