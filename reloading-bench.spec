# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the combined Handloader Bench launcher (Windows build).
# Built by .github/workflows/build-windows.yml on a windows-latest runner --
# see that file for the actual `pyinstaller reloading-bench.spec` invocation
# and the self-signing step that runs after this produces dist/HandloaderBench.exe.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("handloads/schema.sql", "handloads")]
datas += collect_data_files("matplotlib")  # mpl-data: fonts, matplotlibrc, etc.

hiddenimports = ["matplotlib.backends.backend_tkagg"]
hiddenimports += collect_submodules("py_ballisticcalc")  # engines are loaded dynamically by name

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HandloaderBench",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no terminal window -- this is the GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
