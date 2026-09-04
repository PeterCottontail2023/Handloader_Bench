#!/usr/bin/env python3
"""Handloader Bench -- combined launcher for the handloads tracker and the
local ballistics calculator, so both ship as one executable/process.

Only one tk.Tk() root may exist per process; this owns it (hidden) and opens
each tool as a Toplevel from it, so opening one, the other, or both at once
all work from a single launcher window.

Run with:  python3 launcher.py
"""
from __future__ import annotations

import traceback
import tkinter as tk
from tkinter import messagebox, ttk

# handloads.app / ballistics.app are imported lazily (inside the button
# handlers below), not here at module load: matplotlib + py_ballisticcalc
# are only needed if the ballistics tool is actually opened, and this keeps
# the launcher itself opening instantly either way.


class LauncherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Handloader Bench")
        self.geometry("420x280")
        self.resizable(False, False)

        self._handloads_win: tk.Toplevel | None = None
        self._ballistics_win: tk.Toplevel | None = None

        ttk.Label(self, text="Handloader Bench", font=("", 18, "bold")).pack(pady=(28, 4))
        ttk.Label(self, text="Handload records + local ballistics calculator", foreground="gray").pack()

        body = ttk.Frame(self)
        body.pack(expand=True, fill="both", padx=32, pady=24)

        ttk.Button(body, text="Handload Records", command=self._open_handloads).pack(fill="x", pady=6, ipady=10)
        ttk.Button(body, text="Ballistics Calculator", command=self._open_ballistics).pack(fill="x", pady=6, ipady=10)

        ttk.Label(self, text="Close this window to exit both.", foreground="gray").pack(pady=(0, 12))

    def report_callback_exception(self, exc, val, tb) -> None:  # noqa: ANN001 -- Tkinter's own signature
        """Tkinter calls this on any exception a button/event callback raises
        instead of letting it propagate. The default implementation prints to
        sys.stderr -- which doesn't exist in a windowed (console=False) build,
        so the error just vanishes and the button looks like it did nothing.
        Show it instead."""
        text = "".join(traceback.format_exception(exc, val, tb))
        messagebox.showerror("Handloader Bench -- unexpected error", text)

    def _open_handloads(self) -> None:
        if self._handloads_win is not None and self._handloads_win.winfo_exists():
            self._handloads_win.lift()
            self._handloads_win.focus_force()
            return
        from handloads.app import HandloadsApp  # noqa: PLC0415 -- deliberately lazy, see module docstring
        self._handloads_win = HandloadsApp(self)

    def _open_ballistics(self) -> None:
        if self._ballistics_win is not None and self._ballistics_win.winfo_exists():
            self._ballistics_win.lift()
            self._ballistics_win.focus_force()
            return
        from ballistics.app import BallisticsApp  # noqa: PLC0415 -- deliberately lazy, see module docstring
        self._ballistics_win = BallisticsApp(self)


def main() -> None:
    app = LauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
