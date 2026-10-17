"""Patients tab: register, edit and search patients."""
import tkinter as tk
from tkinter import messagebox, ttk

import database as db


class PatientsTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app
        self.selected_id = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Search (name or ID):").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(top, textvariable=self.search_var, width=32).pack(side="left", padx=6)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=10)
        cols = (("code", "Patient ID", 90), ("name", "Name", 200), ("age", "Age", 50),
                ("sex", "Sex", 55), ("tests", "Tests", 55), ("reg", "Registered", 130))
        self.tree = ttk.Treeview(body, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for key, title, width in cols:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(body, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ttk.LabelFrame(body, text="Patient details", padding=12)
        form.pack(side="left", fill="y", padx=(12, 0))
        self.vars = {k: tk.StringVar() for k in ("code", "name", "age", "sex")}
        for i, (key, label) in enumerate([("code", "Patient ID"), ("name", "Full name"),
                                          ("age", "Age"), ("sex", "Sex (optional)")]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=4)
            if key == "sex":
                w = ttk.Combobox(form, textvariable=self.vars[key], values=["", "F", "M", "Other"],
                                 state="readonly", width=18)
            else:
                w = ttk.Entry(form, textvariable=self.vars[key], width=20)
            w.grid(row=i, column=1, padx=(8, 0), pady=4)
        btns = ttk.Frame(form)
        btns.grid(row=4, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        ttk.Button(btns, text="New patient", command=self.new_patient).pack(side="left")
        ttk.Button(btns, text="Save", command=self.save).pack(side="right")
        ttk.Button(form, text="Record test for this patient",
                   command=self._record_test).grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        ttk.Button(form, text="View history",
                   command=self._view_history).grid(row=6, column=0, columnspan=2, pady=(4, 0), sticky="ew")
        self.new_patient()

    def refresh(self):
        keep = self.selected_id
        self.tree.delete(*self.tree.get_children())
        for p in db.list_patients(self.search_var.get()):
            self.tree.insert("", "end", iid=str(p["patient_id"]),
                             values=(p["patient_code"], p["name"], p["age"], p["sex"] or "",
                                     p["n_tests"], p["registered_at"]))
        if keep and self.tree.exists(str(keep)):
            self.tree.selection_set(str(keep))

    def new_patient(self):
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())
        for v in self.vars.values():
            v.set("")
        self.vars["code"].set(db.next_patient_code())

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        code, name, age, sex, *_ = self.tree.item(sel[0], "values")
        for k, v in zip(("code", "name", "age", "sex"), (code, name, age, sex)):
            self.vars[k].set(v)

    def save(self):
        data = [self.vars[k].get() for k in ("code", "name", "age", "sex")]
        try:
            if self.selected_id is None:
                self.selected_id = db.add_patient(*data)
            else:
                db.update_patient(self.selected_id, *data)
        except ValueError as e:
            messagebox.showerror("Cannot save patient", str(e))
            return
        self.app.refresh_all()

    def _record_test(self):
        if self.selected_id is None:
            messagebox.showinfo("Select a patient", "Select or save a patient first.")
            return
        self.app.open_test_entry(self.selected_id)

    def _view_history(self):
        if self.selected_id is None:
            messagebox.showinfo("Select a patient", "Select or save a patient first.")
            return
        self.app.open_history(self.selected_id)
