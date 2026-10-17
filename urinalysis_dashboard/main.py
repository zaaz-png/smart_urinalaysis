"""Smart Urinalysis Monitoring and Diagnostic Dashboard - entry point.

Run:  python main.py
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import database as db
import generate_data
import reports
import validation as V
from analytics import HistoryTab
from patients import PatientsTab
from test_entry import TestEntryTab


class DashboardTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=14)
        self.app = app

        cards = ttk.Frame(self)
        cards.pack(fill="x")
        self.card_vars = {}
        for key, title, color in (("patients", "Patients", "#1565c0"), ("tests", "Tests conducted", "#37474f"),
                                  ("flagged", "Flagged tests", V.FLAG_COLORS["Abnormal"]),
                                  ("pending", "Pending review", V.FLAG_COLORS["Borderline"])):
            box = tk.Frame(cards, bg="white", highlightbackground="#cfd8dc", highlightthickness=1, padx=18, pady=10)
            box.pack(side="left", expand=True, fill="x", padx=5)
            var = tk.StringVar(value="0")
            self.card_vars[key] = var
            tk.Label(box, textvariable=var, font=("Helvetica", 28, "bold"), fg=color, bg="white").pack()
            tk.Label(box, text=title, fg="#546e7a", bg="white").pack()

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(14, 4))
        ttk.Label(bar, text="Recent tests (double-click to open history)",
                  font=("Helvetica", 11, "bold")).pack(side="left")
        for text, cmd in (("Add demo data", self.app.add_demo_data), ("Export CSV", self.app.export_csv),
                          ("Import CSV", self.app.import_csv), ("Reference ranges", self.app.edit_ranges)):
            ttk.Button(bar, text=text, command=cmd).pack(side="right", padx=3)

        cols = (("when", "Test time", 130), ("code", "Patient ID", 80), ("name", "Patient", 190),
                ("source", "Source", 80), ("flags", "Flagged", 70), ("status", "Review status", 110))
        self.tree = ttk.Treeview(self, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for key, title, w in cols:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=w)
        self.tree.tag_configure("Abnormal", background=V.FLAG_BG["Abnormal"])
        self.tree.tag_configure("Borderline", background=V.FLAG_BG["Borderline"])
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._open)
        self._rows = {}

    def refresh(self):
        for key, value in db.stats().items():
            self.card_vars[key].set(str(value))
        self.tree.delete(*self.tree.get_children())
        self._rows.clear()
        for t in db.recent_tests(20):
            tag = "Abnormal" if t["n_abnormal"] else "Borderline" if t["n_borderline"] else ""
            iid = str(t["test_id"])
            self._rows[iid] = t["patient_id"]
            self.tree.insert("", "end", iid=iid, tags=(tag,),
                             values=(t["tested_at"], t["patient_code"], t["name"], t["source"],
                                     t["n_abnormal"] + t["n_borderline"], t["review_status"]))

    def _open(self, _event):
        sel = self.tree.selection()
        if sel:
            self.app.open_history(self._rows[sel[0]], int(sel[0]))


class RangesDialog(tk.Toplevel):
    """Edit the reference interval of each numeric parameter."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Reference ranges")
        self.resizable(False, False)
        self.transient(app)
        frame = ttk.Frame(self, padding=14)
        frame.pack()
        ttk.Label(frame, text="Results outside these limits are flagged Abnormal.\n"
                              "Categorical parameters: Negative is normal, Trace is borderline.",
                  justify="left").grid(row=0, column=0, columnspan=3, pady=(0, 10))
        rules = db.get_rules()
        self.vars = {}
        for i, name in enumerate(V.NUMERIC_NAMES, start=1):
            ttk.Label(frame, text=name).grid(row=i, column=0, sticky="w", pady=4)
            lo, hi = tk.StringVar(value=f"{rules[name][0]:g}"), tk.StringVar(value=f"{rules[name][1]:g}")
            self.vars[name] = (lo, hi)
            ttk.Entry(frame, textvariable=lo, width=8).grid(row=i, column=1, padx=6)
            ttk.Entry(frame, textvariable=hi, width=8).grid(row=i, column=2)
        btns = ttk.Frame(frame)
        btns.grid(row=99, column=0, columnspan=3, pady=(12, 0), sticky="e")
        ttk.Button(btns, text="Reset defaults", command=self.reset).pack(side="left", padx=4)
        ttk.Button(btns, text="Save", command=self.save).pack(side="left")

    def save(self):
        try:
            parsed = {n: (float(lo.get()), float(hi.get())) for n, (lo, hi) in self.vars.items()}
            for n, (lo, hi) in parsed.items():
                db.set_rule(n, lo, hi)
        except ValueError as e:
            messagebox.showerror("Invalid range", str(e) or "Enter numbers only.", parent=self)
            return
        db.reflag_all()
        self.app.refresh_all()
        self.destroy()

    def reset(self):
        db.reset_rules()
        db.reflag_all()
        self.app.refresh_all()
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Urinalysis Monitoring Dashboard")
        self.geometry("1180x740")
        self.minsize(980, 640)
        db.init_db()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.dashboard = DashboardTab(self.nb, self)
        self.patients = PatientsTab(self.nb, self)
        self.entry = TestEntryTab(self.nb, self)
        self.history = HistoryTab(self.nb, self)
        for tab, title in ((self.dashboard, "Dashboard"), (self.patients, "Patients"),
                           (self.entry, "New test"), (self.history, "History & charts")):
            self.nb.add(tab, text=title)
        ttk.Label(self, foreground="#666", padding=6,
                  text="Flagged results are not a diagnosis. Synthetic records are fictional demonstration data."
                  ).pack(fill="x")
        self.refresh_all()
        if db.stats()["patients"] == 0:
            self.after(300, self._offer_demo)

    def refresh_all(self):
        for tab in (self.dashboard, self.patients, self.entry, self.history):
            tab.refresh()

    def open_history(self, patient_id, test_id=None):
        self.history.show_patient(patient_id, test_id)
        self.nb.select(self.history)

    def open_test_entry(self, patient_id):
        self.entry.select_patient(patient_id)
        self.nb.select(self.entry)

    # ----------------------------------------------------------- actions
    def _offer_demo(self):
        if messagebox.askyesno("Empty database", "No records yet. Add synthetic demo patients and tests?"):
            self.add_demo_data(ask=False)

    def add_demo_data(self, ask=True):
        if ask and not messagebox.askyesno("Add demo data", "Add 25 fictional patients with test history?"):
            return
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            patients, tests = generate_data.generate(25, seed=None)
        finally:
            self.config(cursor="")
        self.refresh_all()
        messagebox.showinfo("Demo data", f"Added {patients} patients and {tests} tests (source: Synthetic).")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="urinalysis_export.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            messagebox.showinfo("Export complete", f"Exported {reports.export_csv(path)} tests to\n{path}")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            done, skipped, errors = reports.import_csv(path)
        except (ValueError, OSError) as e:
            messagebox.showerror("Import failed", str(e))
            return
        self.refresh_all()
        detail = "\n".join(errors[:8]) + (f"\n... and {len(errors) - 8} more" if len(errors) > 8 else "")
        messagebox.showinfo("Import finished", f"Imported {done} tests, skipped {skipped}.\n\n{detail}".strip())

    def edit_ranges(self):
        RangesDialog(self)


if __name__ == "__main__":
    App().mainloop()
