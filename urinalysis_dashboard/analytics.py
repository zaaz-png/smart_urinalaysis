"""History tab: a patient's tests, per-test results, review action and trend chart."""
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import database as db
import reports
import validation as V


class HistoryTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app
        self.patient_ids = {}

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Patient").pack(side="left")
        self.patient_var = tk.StringVar()
        self.patient_box = ttk.Combobox(top, textvariable=self.patient_var, state="readonly", width=32)
        self.patient_box.pack(side="left", padx=(6, 18))
        self.patient_box.bind("<<ComboboxSelected>>", lambda _e: self.load_tests())
        ttk.Label(top, text="Chart parameter").pack(side="left")
        self.analyte_var = tk.StringVar(value=V.NAMES[0])
        box = ttk.Combobox(top, textvariable=self.analyte_var, values=V.NAMES, state="readonly", width=18)
        box.pack(side="left", padx=6)
        box.bind("<<ComboboxSelected>>", lambda _e: self.draw_chart())
        ttk.Button(top, text="Export PDF report", command=self.export_pdf).pack(side="right")
        ttk.Button(top, text="Mark reviewed", command=self.mark_reviewed).pack(side="right", padx=6)

        mid = ttk.Frame(self)
        mid.pack(fill="x", pady=10)
        self.tests = ttk.Treeview(mid, columns=("when", "source", "status", "flags"), show="headings",
                                  height=6, selectmode="browse")
        for key, title, w in (("when", "Test time", 130), ("source", "Source", 80),
                              ("status", "Review status", 110), ("flags", "Flagged", 70)):
            self.tests.heading(key, text=title)
            self.tests.column(key, width=w)
        self.tests.pack(side="left", fill="x", expand=True)
        self.tests.bind("<<TreeviewSelect>>", lambda _e: self.show_results())

        self.results = ttk.Treeview(mid, columns=("analyte", "value", "unit", "flag"), show="headings", height=6)
        for key, title, w in (("analyte", "Parameter", 120), ("value", "Result", 70),
                              ("unit", "Unit", 55), ("flag", "Flag", 80)):
            self.results.heading(key, text=title)
            self.results.column(key, width=w)
        self.results.pack(side="left", fill="x", expand=True, padx=(10, 0))
        for tree in (self.tests, self.results):
            tree.tag_configure("Abnormal", background=V.FLAG_BG["Abnormal"])
            tree.tag_configure("Borderline", background=V.FLAG_BG["Borderline"])

        self.fig = Figure(figsize=(7, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------------------------------------------------------- data
    def refresh(self):
        choices = db.patient_choices()
        self.patient_ids = {label: pid for pid, label in choices}
        self.patient_box["values"] = [label for _, label in choices]
        if self.patient_var.get() in self.patient_ids:
            self.load_tests(keep_selection=True)
        else:
            self.patient_var.set("")
            self.load_tests()

    def _pid(self):
        return self.patient_ids.get(self.patient_var.get())

    def show_patient(self, patient_id, test_id=None):
        self.refresh()
        for label, pid in self.patient_ids.items():
            if pid == patient_id:
                self.patient_var.set(label)
        self.load_tests(select=test_id)

    def load_tests(self, select=None, keep_selection=False):
        keep = select or (self.tests.selection()[0] if keep_selection and self.tests.selection() else None)
        self.tests.delete(*self.tests.get_children())
        pid = self._pid()
        rows = db.tests_for_patient(pid) if pid else []
        for t in rows:
            tag = "Abnormal" if t["n_abnormal"] else "Borderline" if t["n_borderline"] else ""
            self.tests.insert("", "end", iid=str(t["test_id"]), tags=(tag,),
                              values=(t["tested_at"], t["source"], t["review_status"],
                                      t["n_abnormal"] + t["n_borderline"]))
        first = str(keep) if keep and self.tests.exists(str(keep)) else (self.tests.get_children() or [None])[0]
        if first:
            self.tests.selection_set(first)
            self.tests.see(first)
        self.show_results()
        self.draw_chart()

    def _selected_test(self):
        sel = self.tests.selection()
        return int(sel[0]) if sel else None

    def show_results(self):
        self.results.delete(*self.results.get_children())
        tid = self._selected_test()
        if tid is None:
            return
        _, rows = db.test_detail(tid)
        for r in rows:
            self.results.insert("", "end", tags=(r["flag"],),
                                values=(r["analyte"], r["value"], r["unit"] or "", r["flag"]))

    # ------------------------------------------------------------- actions
    def mark_reviewed(self):
        tid = self._selected_test()
        if tid is None:
            messagebox.showinfo("Select a test", "Select a test in the list first.")
            return
        db.set_review(tid, "Reviewed")
        self.app.refresh_all()

    def export_pdf(self):
        tid = self._selected_test()
        if tid is None:
            messagebox.showinfo("Select a test", "Select a test in the list first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"urinalysis_{tid}.pdf",
                                            filetypes=[("PDF", "*.pdf")])
        if path:
            try:
                reports.generate_test_report(tid, path)
                messagebox.showinfo("Report saved", path)
            except Exception as e:
                messagebox.showerror("Report failed", str(e))

    # --------------------------------------------------------------- chart
    def draw_chart(self):
        ax = self.ax
        ax.clear()
        pid, name = self._pid(), self.analyte_var.get()
        hist = db.analyte_history(pid, name) if pid else []
        if not hist:
            ax.text(0.5, 0.5, "No results to chart" if pid else "Select a patient",
                    ha="center", va="center", transform=ax.transAxes, color="#777")
            ax.set_axis_off()
            self.canvas.draw_idle()
            return
        ax.set_axis_on()
        spec = V.BY_NAME[name]
        xs = [datetime.strptime(h["tested_at"], db.TIME_FMT) for h in hist]
        ys = [V.grade(name, h["value"]) for h in hist]
        if spec["kind"] == "numeric":
            low, high = db.get_rules()[name]
            ax.axhspan(low, high, color="#2e7d32", alpha=0.12, label="Reference range")
            ax.set_ylabel(f"{name} {spec['unit']}".strip())
        else:
            opts = spec["options"]
            ax.axhspan(-0.5, 0.5, color="#2e7d32", alpha=0.12, label="Reference (negative)")
            ax.set_yticks(range(len(opts)))
            ax.set_yticklabels(opts)
            ax.set_ylim(-0.6, len(opts) - 0.4)
        ax.plot(xs, ys, color="#78909c", linewidth=1.2, zorder=1)
        ax.scatter(xs, ys, c=[V.FLAG_COLORS[h["flag"]] for h in hist], s=42, zorder=2)
        ax.set_title(f"{name} over time", fontsize=10)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper left", fontsize=8)
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.canvas.draw_idle()
