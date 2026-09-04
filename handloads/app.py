#!/usr/bin/env python3
"""Handloading records tracker -- local Tkinter GUI over a local SQLite database.

Runnable three ways: standalone (python3 app.py), imported as the
handloads.app submodule by the combined launcher (../launcher.py), or frozen
by PyInstaller as part of it.

Run with:  python3 app.py
No external dependencies; data stays in handloads.db next to this file.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, filedialog, ttk
from typing import Any, Callable

# Put the repo root on sys.path so `handloads` resolves as a proper package
# (dotted import below) -- this is the form that actually works once
# PyInstaller freezes this: a frozen build loads bundled modules from its own
# embedded archive by dotted name, not from real files on disk, so a
# directory-based sys.path trick pointing at this file's own folder (which
# doesn't exist as a real directory in a frozen build) silently finds nothing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from handloads import db  # noqa: E402
except ImportError:
    # Pure standalone (`cd handloads && python3 app.py`, unfrozen): the repo
    # root above isn't actually meaningful, but this file's own directory is
    # already on sys.path automatically in that mode -- bare import db.py directly.
    import db  # noqa: E402

# (label, db_column, kind) -- kind is "str", "int", or "float"
LOAD_FIELDS: list[tuple[str, str, str]] = [
    ("Date loaded (YYYY-MM-DD)", "date_loaded", "str"),
    ("Date tested (YYYY-MM-DD)", "date_tested", "str"),
    ("Caliber", "caliber", "str"),
    ("Status (Proven/Untested/etc.)", "status", "str"),
    ("Case manufacturer", "case_mfr", "str"),
    ("Case lot", "case_lot", "str"),
    ("Times fired (this brass)", "times_fired", "int"),
    ("Primer manufacturer", "primer_mfr", "str"),
    ("Primer type", "primer_type", "str"),
    ("Powder manufacturer", "powder_mfr", "str"),
    ("Powder type", "powder_type", "str"),
    ("Charge weight (gr)", "charge_weight_gr", "float"),
    ("Bullet manufacturer", "bullet_mfr", "str"),
    ("Bullet weight (gr)", "bullet_weight_gr", "float"),
    ("Bullet type", "bullet_type", "str"),
    ("Bullet diameter (in)", "bullet_diameter_in", "float"),
    ("Bullet length (in)", "bullet_length_in", "float"),
    ("Ballistic coefficient", "ballistic_coefficient", "float"),
    ("BC drag model (G1/G7)", "bc_drag_model", "str"),
    ("COAL (in)", "coal_in", "float"),
    ("Seating depth note", "seating_depth_note", "str"),
    ("Crimp", "crimp", "str"),
    ("Num rounds tested", "num_rounds", "int"),
    ("Avg velocity (fps)", "avg_velocity_fps", "float"),
    ("SD (fps)", "sd_fps", "float"),
    ("ES (fps)", "es_fps", "float"),
    ("Group size (in)", "group_size_in", "float"),
    ("Group distance (yd)", "group_distance_yd", "float"),
    ("Pressure (PSI, published)", "pressure_psi", "float"),
    ("Load density (%, published)", "load_density_pct", "float"),
    ("Pressure signs (your own)", "pressure_signs", "str"),
    ("Temperature (F)", "temperature_f", "float"),
    ("Weather notes", "weather_notes", "str"),
    ("Notes", "notes", "str"),
    ("Comments", "comments", "str"),
]

FIREARM_FIELDS: list[tuple[str, str, str]] = [
    ("Nickname", "name", "str"),
    ("Make", "make", "str"),
    ("Model", "model", "str"),
    ("Caliber", "caliber", "str"),
    ("Barrel length (in)", "barrel_length_in", "float"),
    ("Twist rate", "twist_rate", "str"),
    ("Action type", "action_type", "str"),
    ("Notes", "notes", "str"),
]

TREE_COLUMNS = [
    ("date", "Date", 90),
    ("firearm", "Firearm", 150),
    ("caliber", "Caliber", 80),
    ("status", "Status", 90),
    ("bullet", "Bullet", 160),
    ("powder", "Powder / Charge", 150),
    ("coal", "COAL", 60),
    ("velocity", "Vel (fps)", 90),
    ("group", "Group", 90),
]


def parse_value(raw: str, kind: str) -> Any:
    raw = raw.strip()
    if not raw:
        return None
    if kind == "int":
        return int(raw)
    if kind == "float":
        return float(raw)
    return raw


def to_display(value: Any) -> str:
    return "" if value is None else str(value)


class ScrollableForm(ttk.Frame):
    """A label+entry grid for a list of fields, with widgets accessible by column key."""

    def __init__(self, parent: tk.Widget, fields: list[tuple[str, str, str]]):
        super().__init__(parent)
        self.fields = fields
        self.widgets: dict[str, tk.Entry] = {}
        for row, (label, key, _kind) in enumerate(fields):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
            entry = ttk.Entry(self, width=40)
            entry.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
            self.widgets[key] = entry
        self.columnconfigure(1, weight=1)

    def get_values(self) -> dict[str, Any]:
        values = {}
        for label, key, kind in self.fields:
            try:
                values[key] = parse_value(self.widgets[key].get(), kind)
            except ValueError:
                raise ValueError(f"'{label}' must be a number")
        return values

    def set_values(self, row: Any) -> None:
        for _label, key, _kind in self.fields:
            entry = self.widgets[key]
            entry.delete(0, tk.END)
            if row is not None and key in row.keys():
                entry.insert(0, to_display(row[key]))


class FirearmDialog(tk.Toplevel):
    """Manage firearms: list + add/edit/delete."""

    def __init__(self, parent: tk.Widget, on_change: Callable[[], None]):
        super().__init__(parent)
        self.title("Manage firearms")
        self.geometry("560x420")
        self.on_change = on_change
        self.selected_id: int | None = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)
        self.listbox = tk.Listbox(left, width=28, exportselection=False)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.form = ScrollableForm(right, FIREARM_FIELDS)
        self.form.pack(fill="both", expand=True)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="New", command=self._new).pack(side="left")
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left")
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right")

        self._refresh_list()

    def _refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        self.rows = db.list_firearms()
        for row in self.rows:
            self.listbox.insert(tk.END, f"{row['name']} ({row['caliber']})")

    def _on_select(self, _event: object) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        row = self.rows[sel[0]]
        self.selected_id = row["id"]
        self.form.set_values(row)

    def _new(self) -> None:
        self.selected_id = None
        self.form.set_values(None)

    def _save(self) -> None:
        try:
            values = self.form.get_values()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            return
        if not values.get("name") or not values.get("caliber"):
            messagebox.showerror("Missing fields", "Nickname and caliber are required.", parent=self)
            return
        if self.selected_id is None:
            db.add_firearm(values)
        else:
            db.update_firearm(self.selected_id, values)
        self._refresh_list()
        self.on_change()

    def _delete(self) -> None:
        if self.selected_id is None:
            return
        if messagebox.askyesno("Delete firearm", "Delete this firearm? Loads referencing it keep their data but lose the link.", parent=self):
            db.delete_firearm(self.selected_id)
            self.selected_id = None
            self.form.set_values(None)
            self._refresh_list()
            self.on_change()


class LoadDialog(tk.Toplevel):
    """Add or edit a single load record."""

    def __init__(self, parent: tk.Widget, on_save: Callable[[], None], load_id: int | None = None):
        super().__init__(parent)
        self.title("Edit load" if load_id else "New load")
        self.geometry("520x640")
        self.on_save = on_save
        self.load_id = load_id

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(top, text="Firearm:").pack(side="left")
        self.firearm_var = tk.StringVar()
        self.firearm_combo = ttk.Combobox(top, textvariable=self.firearm_var, state="readonly", width=40)
        self.firearm_combo.pack(side="left", padx=6)
        self._load_firearm_options()

        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.form = ScrollableForm(canvas, LOAD_FIELDS)
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="left", fill="y", pady=8)
        self.form.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))

        shot_frame = ttk.LabelFrame(self, text="Chrono shot string (comma-separated fps, optional)")
        shot_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.shot_entry = ttk.Entry(shot_frame)
        self.shot_entry.pack(fill="x", padx=6, pady=6)
        ttk.Label(
            shot_frame,
            text="If filled in, avg/SD/ES above are recalculated from these on save.",
            foreground="gray",
        ).pack(anchor="w", padx=6)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)

        if load_id is not None:
            self._populate(load_id)

    def _load_firearm_options(self) -> None:
        self.firearms = db.list_firearms()
        self.firearm_combo["values"] = ["(none)"] + [f"{r['id']}: {r['name']} ({r['caliber']})" for r in self.firearms]
        self.firearm_combo.current(0)

    def _populate(self, load_id: int) -> None:
        row = db.get_load(load_id)
        if row is None:
            return
        self.form.set_values(row)
        if row["firearm_id"] is not None:
            for i, val in enumerate(self.firearm_combo["values"]):
                if val.startswith(f"{row['firearm_id']}:"):
                    self.firearm_combo.current(i)
                    break
        shots = db.list_shot_strings(load_id)
        if shots:
            self.shot_entry.insert(0, ", ".join(str(s["velocity_fps"]) for s in shots))

    def _selected_firearm_id(self) -> int | None:
        val = self.firearm_var.get()
        if not val or val == "(none)":
            return None
        return int(val.split(":")[0])

    def _save(self) -> None:
        try:
            values = self.form.get_values()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            return
        values["firearm_id"] = self._selected_firearm_id()

        if self.load_id is None:
            new_id = db.add_load(values)
        else:
            db.update_load(self.load_id, values)
            new_id = self.load_id

        shot_text = self.shot_entry.get().strip()
        if shot_text:
            try:
                velocities = [float(v.strip()) for v in shot_text.split(",") if v.strip()]
            except ValueError:
                messagebox.showerror("Invalid input", "Shot string must be comma-separated numbers.", parent=self)
                return
            db.set_shot_strings(new_id, velocities)

        self.on_save()
        self.destroy()


class HandloadsApp(tk.Toplevel):
    """The handloads window. Takes a Tk root as master -- standalone use (main(),
    below) creates a hidden root for it; the combined launcher passes its own
    root so both tools can share one Tcl interpreter/process."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        db.init_db()
        self.title("Handloading Records")
        self.geometry("980x560")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=8)
        ttk.Button(toolbar, text="New load", command=self._new_load).pack(side="left")
        ttk.Button(toolbar, text="Edit load", command=self._edit_selected).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete load", command=self._delete_selected).pack(side="left")
        ttk.Button(toolbar, text="Manage firearms", command=self._manage_firearms).pack(side="left", padx=12)
        ttk.Button(toolbar, text="Export CSV", command=self._export_csv).pack(side="left")
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left", padx=4)

        ttk.Label(toolbar, text="Search:").pack(side="left", padx=(20, 4))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side="left")
        search_entry.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(toolbar, text="Go", command=self.refresh).pack(side="left", padx=4)

        columns = [c for c, _label, _w in TREE_COLUMNS]
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for key, label, width in TREE_COLUMNS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda _e: self._edit_selected())

        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=8, pady=(0, 6))

        self.row_ids: list[int] = []
        self.refresh()

    def refresh(self) -> None:
        rows = db.list_loads(self.search_var.get().strip() or None)
        self.tree.delete(*self.tree.get_children())
        self.row_ids = []
        for row in rows:
            date = row["date_tested"] or row["date_loaded"] or ""
            bullet = " ".join(filter(None, [
                to_display(row["bullet_weight_gr"]) + "gr" if row["bullet_weight_gr"] else "",
                row["bullet_mfr"], row["bullet_type"],
            ])).strip()
            powder = " ".join(filter(None, [
                row["powder_mfr"], row["powder_type"],
                f"@ {row['charge_weight_gr']}gr" if row["charge_weight_gr"] else "",
            ])).strip()
            group = f"{row['group_size_in']}\" @ {row['group_distance_yd']}yd" if row["group_size_in"] else ""
            self.tree.insert("", tk.END, values=(
                date,
                row["firearm_name"] or "",
                row["caliber"] or "",
                row["status"] or "",
                bullet,
                powder,
                to_display(row["coal_in"]),
                to_display(row["avg_velocity_fps"]),
                group,
            ))
            self.row_ids.append(row["id"])
        self.status.set(f"{len(rows)} load record(s)")

    def _selected_load_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        index = self.tree.index(sel[0])
        return self.row_ids[index]

    def _new_load(self) -> None:
        if not db.list_firearms():
            if messagebox.askyesno(
                "No firearms yet",
                "You haven't added any firearms yet. Add one now?",
            ):
                self._manage_firearms()
        LoadDialog(self, on_save=self.refresh)

    def _edit_selected(self) -> None:
        load_id = self._selected_load_id()
        if load_id is None:
            messagebox.showinfo("No selection", "Select a load first.")
            return
        LoadDialog(self, on_save=self.refresh, load_id=load_id)

    def _delete_selected(self) -> None:
        load_id = self._selected_load_id()
        if load_id is None:
            messagebox.showinfo("No selection", "Select a load first.")
            return
        if messagebox.askyesno("Delete load", "Delete this load record? This cannot be undone."):
            db.delete_load(load_id)
            self.refresh()

    def _manage_firearms(self) -> None:
        FirearmDialog(self, on_change=self.refresh)

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="handloads_export.csv",
        )
        if not path:
            return
        count = db.export_csv(Path(path))
        messagebox.showinfo("Export complete", f"Exported {count} record(s) to:\n{path}")


def main() -> None:
    """Standalone entry point: python3 app.py. Creates its own hidden root so
    HandloadsApp (a Toplevel) has something to attach to; closing the window
    exits the whole process, matching the old tk.Tk()-root behavior."""
    root = tk.Tk()
    root.withdraw()
    app = HandloadsApp(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
