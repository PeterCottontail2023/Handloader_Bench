#!/usr/bin/env python3
"""Local ballistic trajectory calculator -- a JBM-Ballistics-style local tool.

Point-mass trajectory math comes from py_ballisticcalc (vendored in ./vendor,
see trajectory.py) -- a direct Python descendant of JBM Ballistics' own
published solver. This file is just the GUI: an input form, a multi-load
drop-vs-range comparison chart (matplotlib embedded in Tkinter), a full
trajectory table, and an optional picker that pulls bullet weight/velocity/BC
straight from the handloads.db database from the other project.

Runnable three ways, all handled by the sys.path setup below: standalone
(python3 app.py), imported as the ballistics.app submodule by the combined
launcher (../launcher.py), or frozen by PyInstaller as part of it.

Run with:  python3 app.py
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
# Put the repo root on sys.path so `ballistics` and `handloads` resolve as
# proper packages (dotted imports below) -- this is the form that actually
# works once PyInstaller freezes this: a frozen build loads bundled modules
# from its own embedded archive by dotted name, not from real files on disk,
# so directory-based sys.path tricks (an earlier version of this file used
# that -- don't go back to it) silently fail to find anything there.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(APP_DIR / "vendor"))  # matplotlib is vendored there, same as py_ballisticcalc

# Keep matplotlib's font/config cache local to this project instead of
# fighting a possibly-read-only home config dir on some systems.
os.environ.setdefault("MPLCONFIGDIR", str(APP_DIR / ".mplcache"))

import matplotlib  # noqa: E402

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_tkagg import (  # noqa: E402
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)

from ballistics.trajectory import compute_trajectory  # noqa: E402
# ^ absolute dotted import: this package is itself named "ballistics", so
# `from ballistics import compute_trajectory` (bare package-relative form)
# would resolve against the *package* (empty __init__.py) and fail with
# AttributeError -- go through the submodule explicitly instead.

# --- Optional integration with the handloads.db project (sibling package) --
# Not a filesystem `.exists()` check: that looks for a real db.py file on
# disk, which isn't there in a frozen build (bundled modules live in the
# embedded archive, not as loose files) -- try the actual import and see.
handloads_db: Any = None
try:
    from handloads import db as handloads_db  # type: ignore[import-not-found,no-redef]
except Exception:
    handloads_db = None

DRAG_MODELS = ["G1", "G7"]

# (label, key, kind, default) -- kind is "float", "float_or_none", or "drag_model"
INPUT_FIELDS: list[tuple[str, str, str, Any]] = [
    ("Bullet weight (gr)", "weight_gr", "float", 180.0),
    ("Muzzle velocity (fps)", "muzzle_velocity_fps", "float", 2700.0),
    ("Ballistic coefficient", "bc", "float", 0.450),
    ("Drag model", "drag_model", "drag_model", "G1"),
    ("Bullet diameter (in, optional)", "diameter_in", "float", 0.0),
    ("Bullet length (in, optional)", "length_in", "float", 0.0),
    ("Twist rate (in/turn, 0 = no spin drift)", "twist_in", "float", 0.0),
    ("Sight height (in)", "sight_height_in", "float", 1.5),
    ("Zero range (yd)", "zero_range_yd", "float", 100.0),
    ("Look angle up/downhill (deg)", "look_angle_deg", "float", 0.0),
    ("Altitude (ft)", "altitude_ft", "float", 0.0),
    ("Pressure (inHg, blank = standard)", "pressure_inhg", "float_or_none", None),
    ("Temperature (F)", "temperature_f", "float", 59.0),
    ("Humidity (%)", "humidity_pct", "float", 0.0),
    ("Wind speed (mph)", "wind_speed_mph", "float", 0.0),
    ("Wind dir (deg, 0=behind, 90=from left)", "wind_direction_deg", "float", 0.0),
    ("Max range (yd)", "max_range_yd", "float", 500.0),
    ("Range step (yd)", "range_step_yd", "float", 25.0),
]

TABLE_COLUMNS = [
    ("range_yd", "Range (yd)", 80),
    ("time_s", "Time (s)", 70),
    ("velocity_fps", "Vel (fps)", 80),
    ("mach", "Mach", 60),
    ("drop_in", "Drop (in)", 80),
    ("drop_moa", "Drop (MOA)", 80),
    ("windage_in", "Wind (in)", 80),
    ("windage_moa", "Wind (MOA)", 80),
    ("energy_ftlb", "Energy (ft-lb)", 100),
]

CURVE_COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]


def parse_field(raw: str, kind: str, default: Any) -> Any:
    raw = raw.strip()
    if not raw:
        return default
    if kind in ("float", "float_or_none"):
        return float(raw)
    return raw


class InputForm(ttk.Frame):
    """Scrollable label+entry grid for INPUT_FIELDS, plus a drag-model combobox."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, width=320)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.widgets: dict[str, tk.Widget] = {}
        for row, (label, key, kind, default) in enumerate(INPUT_FIELDS):
            ttk.Label(inner, text=label, wraplength=170).grid(row=row, column=0, sticky="w", padx=4, pady=3)
            if kind == "drag_model":
                var = tk.StringVar(value=default)
                widget: tk.Widget = ttk.Combobox(inner, textvariable=var, values=DRAG_MODELS, state="readonly", width=17)
                widget.var = var  # type: ignore[attr-defined]
            else:
                widget = ttk.Entry(inner, width=20)
                widget.insert(0, "" if default is None else str(default))
            widget.grid(row=row, column=1, padx=4, pady=3, sticky="ew")
            self.widgets[key] = widget
        inner.columnconfigure(1, weight=1)

    def get_values(self) -> dict[str, Any]:
        values = {}
        for label, key, kind, default in INPUT_FIELDS:
            widget = self.widgets[key]
            if kind == "drag_model":
                values[key] = widget.var.get()  # type: ignore[attr-defined]
            else:
                raw = widget.get()  # type: ignore[union-attr]
                try:
                    values[key] = parse_field(raw, kind, default)
                except ValueError:
                    raise ValueError(f"'{label}' must be a number")
        return values

    def set_values(self, values: dict[str, Any]) -> None:
        for _label, key, kind, _default in INPUT_FIELDS:
            if key not in values or values[key] is None:
                continue
            widget = self.widgets[key]
            if kind == "drag_model":
                widget.var.set(values[key])  # type: ignore[attr-defined]
            else:
                widget.delete(0, tk.END)  # type: ignore[union-attr]
                widget.insert(0, str(values[key]))  # type: ignore[union-attr]


class HandloadPickerDialog(tk.Toplevel):
    """Pick a load from handloads.db to pre-fill weight/velocity/BC/diameter/length."""

    def __init__(self, parent: tk.Widget, on_pick: Callable[[dict[str, Any], str], None]):
        super().__init__(parent)
        self.title("Load from handloads.db")
        self.geometry("720x420")
        self.on_pick = on_pick

        columns = ["firearm", "bullet", "bc", "status"]
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        headers = {"firearm": "Firearm", "bullet": "Bullet", "bc": "BC", "status": "Status"}
        widths = {"firearm": 200, "bullet": 220, "bc": 70, "status": 160}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<Double-1>", lambda _e: self._select())

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="Use selected load", command=self._select).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)

        self.rows = handloads_db.list_loads() if handloads_db else []
        for row in self.rows:
            bullet = " ".join(filter(None, [
                f"{row['bullet_weight_gr']:g}gr" if row["bullet_weight_gr"] else "",
                row["bullet_mfr"], row["bullet_type"],
            ])).strip()
            bc = f"{row['ballistic_coefficient']:.3f} {row['bc_drag_model'] or ''}".strip() \
                if row["ballistic_coefficient"] else "(not set)"
            self.tree.insert("", tk.END, values=(row["firearm_name"] or "", bullet, bc, row["status"] or ""))

    def _select(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        index = self.tree.index(sel[0])
        row = self.rows[index]
        values: dict[str, Any] = {}
        missing = []
        if row["bullet_weight_gr"]:
            values["weight_gr"] = row["bullet_weight_gr"]
        else:
            missing.append("bullet weight")
        if row["avg_velocity_fps"]:
            values["muzzle_velocity_fps"] = row["avg_velocity_fps"]
        else:
            missing.append("velocity")
        if row["ballistic_coefficient"]:
            values["bc"] = row["ballistic_coefficient"]
            if row["bc_drag_model"] in DRAG_MODELS:
                values["drag_model"] = row["bc_drag_model"]
        else:
            missing.append("ballistic coefficient (edit this load in the handloads app to add it)")
        if row["bullet_diameter_in"]:
            values["diameter_in"] = row["bullet_diameter_in"]
        if row["bullet_length_in"]:
            values["length_in"] = row["bullet_length_in"]

        bullet_desc = " ".join(filter(None, [
            f"{row['bullet_weight_gr']:g}gr" if row["bullet_weight_gr"] else "",
            row["bullet_mfr"], row["bullet_type"],
        ])).strip()
        curve_name = f"{row['firearm_name'] or 'Load'} - {bullet_desc}".strip(" -")

        if missing:
            messagebox.showwarning(
                "Some fields missing",
                "This load is missing: " + ", ".join(missing) + ".\n"
                "Filled in what was available; fill in the rest by hand.",
                parent=self,
            )
        self.on_pick(values, curve_name)
        self.destroy()


class BallisticsApp(tk.Toplevel):
    """The ballistics calculator window. Takes a Tk root as master -- standalone
    use (main(), below) creates a hidden root for it; the combined launcher
    passes its own root so both tools can share one Tcl interpreter/process."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Local Ballistics Calculator")
        self.geometry("1280x800")

        self.pinned_curves: dict[str, list[dict[str, Any]]] = {}
        self.current_rows: list[dict[str, Any]] = []

        # --- left: input form + actions ---
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)

        ttk.Button(
            left, text="Load from Handloads...", command=self._open_picker,
            state="normal" if handloads_db else "disabled",
        ).pack(fill="x", pady=(0, 4))
        if not handloads_db:
            ttk.Label(
                left, text="(handloads.db not found alongside this project)",
                foreground="gray", wraplength=300,
            ).pack(fill="x")

        self.form = InputForm(left)
        self.form.pack(fill="both", expand=True, pady=8)

        ttk.Button(left, text="Compute", command=self._compute).pack(fill="x", pady=(4, 2))

        curve_row = ttk.Frame(left)
        curve_row.pack(fill="x", pady=2)
        ttk.Label(curve_row, text="Curve name:").pack(side="left")
        self.curve_name_var = tk.StringVar(value="Load 1")
        ttk.Entry(curve_row, textvariable=self.curve_name_var).pack(side="left", fill="x", expand=True, padx=4)

        ttk.Button(left, text="Add / Update Curve on Chart", command=self._add_curve).pack(fill="x", pady=2)

        ttk.Label(left, text="Curves on chart:").pack(fill="x", pady=(10, 2))
        self.curve_listbox = tk.Listbox(left, height=6)
        self.curve_listbox.pack(fill="x")
        curve_btns = ttk.Frame(left)
        curve_btns.pack(fill="x", pady=2)
        ttk.Button(curve_btns, text="Remove Selected", command=self._remove_curve).pack(side="left")
        ttk.Button(curve_btns, text="Clear All", command=self._clear_curves).pack(side="left", padx=4)

        # --- right: chart (top) + trajectory table (bottom) ---
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.fig, self.ax = plt.subplots(figsize=(7, 4.5), dpi=100)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, right)
        toolbar.update()

        table_frame = ttk.LabelFrame(right, text="Trajectory table (current inputs)")
        table_frame.pack(fill="both", expand=True, pady=(8, 0))
        columns = [c for c, _l, _w in TABLE_COLUMNS]
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for key, label, width in TABLE_COLUMNS:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, anchor="e")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)
        self.table.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

    # ------------------------------------------------------------ actions --

    def _open_picker(self) -> None:
        HandloadPickerDialog(self, on_pick=self._apply_picked_load)

    def _apply_picked_load(self, values: dict[str, Any], curve_name: str) -> None:
        self.form.set_values(values)
        self.curve_name_var.set(curve_name)

    def _compute(self) -> list[dict[str, Any]] | None:
        try:
            values = self.form.get_values()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return None
        try:
            rows = compute_trajectory(**values)
        except ValueError as exc:
            messagebox.showerror("Calculation error", str(exc))
            return None
        self.current_rows = rows
        self._populate_table(rows)
        self._redraw_chart(preview_rows=rows, preview_name=self.curve_name_var.get() or "(current)")
        return rows

    def _add_curve(self) -> None:
        rows = self._compute()
        if rows is None:
            return
        name = self.curve_name_var.get().strip() or f"Load {len(self.pinned_curves) + 1}"
        is_new = name not in self.pinned_curves
        self.pinned_curves[name] = rows
        if is_new:
            self.curve_listbox.insert(tk.END, name)
        self._redraw_chart()

    def _remove_curve(self) -> None:
        sel = self.curve_listbox.curselection()
        if not sel:
            return
        name = self.curve_listbox.get(sel[0])
        self.pinned_curves.pop(name, None)
        self.curve_listbox.delete(sel[0])
        self._redraw_chart()

    def _clear_curves(self) -> None:
        self.pinned_curves.clear()
        self.curve_listbox.delete(0, tk.END)
        self._redraw_chart()

    # -------------------------------------------------------------- views --

    def _populate_table(self, rows: list[dict[str, Any]]) -> None:
        self.table.delete(*self.table.get_children())
        for r in rows:
            self.table.insert("", tk.END, values=(
                f"{r['range_yd']:.0f}", f"{r['time_s']:.3f}", f"{r['velocity_fps']:.1f}",
                f"{r['mach']:.2f}", f"{r['drop_in']:.2f}", f"{r['drop_moa']:.2f}",
                f"{r['windage_in']:.2f}", f"{r['windage_moa']:.2f}", f"{r['energy_ftlb']:.0f}",
            ))

    def _style_axes(self) -> None:
        self.ax.clear()
        self.ax.set_title("Drop vs Range")
        self.ax.set_xlabel("Range (yd)")
        self.ax.set_ylabel("Drop relative to line of sight (in)")
        self.ax.axhline(0, color="#999", linewidth=0.8, linestyle="--")
        self.ax.grid(True, alpha=0.3)

    def _redraw_chart(self, preview_rows: list[dict[str, Any]] | None = None, preview_name: str = "") -> None:
        self._style_axes()
        color_i = 0
        for name, rows in self.pinned_curves.items():
            xs = [r["range_yd"] for r in rows]
            ys = [r["drop_in"] for r in rows]
            self.ax.plot(xs, ys, label=name, color=CURVE_COLORS[color_i % len(CURVE_COLORS)], linewidth=1.8)
            color_i += 1
        if preview_rows is not None and preview_name not in self.pinned_curves:
            xs = [r["range_yd"] for r in preview_rows]
            ys = [r["drop_in"] for r in preview_rows]
            self.ax.plot(xs, ys, label=f"{preview_name} (preview)", color="black",
                         linewidth=1.2, linestyle=":")
        if self.pinned_curves or preview_rows is not None:
            self.ax.legend(fontsize=8, loc="best")
        self.fig.tight_layout()
        self.canvas.draw()


def main() -> None:
    """Standalone entry point: python3 app.py. Creates its own hidden root so
    BallisticsApp (a Toplevel) has something to attach to; closing the window
    exits the whole process, matching the old tk.Tk()-root behavior."""
    root = tk.Tk()
    root.withdraw()
    app = BallisticsApp(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
