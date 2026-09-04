# Building Handloader Bench

Maintainer-facing notes on the combined launcher and the Windows build
pipeline. If you just want to *use* the app, see `README.md` instead.

## How the combined build works

`launcher.py` owns the single `tk.Tk()` root a process is allowed to have;
`HandloadsApp` and `BallisticsApp` were changed from `tk.Tk` to `tk.Toplevel`
subclasses so either (or both) can open as windows under that one root --
that's what makes "one executable" possible instead of two.

Both tools' `app.py` files are still independently runnable scripts too
(`python3 app.py` inside either directory). Cross-module imports (each tool
importing its own sibling module, and `ballistics` optionally reading
`handloads`' `db.py`) use absolute dotted imports (`from handloads import
db`, `from ballistics.trajectory import compute_trajectory`) rather than
directory-based `sys.path` tricks -- the latter looks tempting for a quick
fix but silently resolves nothing once frozen, since PyInstaller loads
bundled modules from its own embedded archive by name, not from real files
on disk. See the comments at the top of each `app.py` if you're extending
this.

**Data persistence**: `handloads/db.py` writes `handloads.db` next to itself
during normal dev use, but under a frozen build that would put it inside
PyInstaller's temporary extraction folder -- wiped after every run. Frozen
builds instead write to `%APPDATA%\HandloaderBench\handloads.db`, so data
survives between launches. Nobody's real reloading log ships inside the
built .exe -- `.gitignore` excludes `*.db`, so every install starts with an
empty database (schema only) on first run, exactly like a fresh clone here.

## Building the Windows .exe

Push to GitHub, then either push a version tag or trigger it by hand:

```
git tag vX.Y.Z
git push --tags
```

or: repo's Actions tab -> "Build Windows executable" -> Run workflow.

GitHub's own `windows-latest` runner does the actual build (real Windows
Python + Tcl/Tk + PyInstaller -- nothing here is cross-compiled or emulated).
Download the result from the workflow run's Artifacts section, or from the
release page if you pushed a tag.

**A build that errors on launch is almost always a hidden-import fix.**
matplotlib + a dynamically-loading library like py_ballisticcalc are the
single most common source of "ModuleNotFoundError" in a *frozen* app that
imports fine unfrozen. `reloading-bench.spec`'s `hiddenimports` is seeded
with the packages most likely to need it, but hasn't been exhaustively
verified against every Windows/Python combination. The fix: read the error
for the missing module name, add it to `hiddenimports` in
`reloading-bench.spec`, commit, rebuild. (A frozen, windowed build swallows
unhandled exceptions with no visible error at all, since there's no console
to print a traceback to -- `launcher.py`'s `report_callback_exception`
override turns those into a message box instead, so an in-app bug should
surface a real error rather than a dead button.)

## Signing

The workflow self-signs the .exe (`Set-AuthenticodeSignature`, a fresh
ephemeral cert generated each build) -- this makes the file **tamper-evident**
(proves it's exactly what this build produced) but Windows SmartScreen will
still show an "unknown publisher" warning on first run, since the cert isn't
rooted in a certificate authority Windows already trusts. That's expected
for a free tool without a purchased code-signing certificate.

Getting a real certificate (from a CA, or a free one via a program like
SignPath.io for open-source projects) and wiring it in removes the warning
for good, via two changes:
1. Store the certificate (as a base64-encoded `.pfx` + its password) as
   GitHub Actions secrets in this repo.
2. Swap the self-signing step in `.github/workflows/build-windows.yml` for
   one that imports that secret and signs with it instead.
