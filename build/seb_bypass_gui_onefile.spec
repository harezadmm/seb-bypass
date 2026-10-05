#!/usr/bin/env python3
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec ONEFILE untuk Windows: satu file .exe.

Dipakai build_windows.ps1 (dan workflow CI). Untuk macOS tetap pakai
seb_bypass_gui.spec (mode onedir + BUNDLE .app), karena .app memang
berupa folder.
"""
import os
import sys

HERE = os.path.abspath(os.path.dirname(SPEC))  # noqa: F821
SRCDIR = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(SRCDIR, "seb_bypass_gui.py")
if not os.path.isfile(SCRIPT):
    SCRIPT = os.path.join(HERE, "seb_bypass_gui.py")

ICON = os.path.join(HERE, "assets", "sebstudio.ico")
if not os.path.isfile(ICON):
    ICON = None

a = Analysis(  # noqa: F821
    [SCRIPT],
    pathex=[SRCDIR, HERE],
    binaries=[],
    datas=[],
    hiddenimports=["tkinter", "tkinter.ttk", "tkinter.filedialog",
                   "tkinter.messagebox", "plistlib"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib", "scipy", "PyQt5", "PySide2",
              "test", "unittest", "pydoc", "xmlrpc", "PIL"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SEB Config Bypass Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI: tanpa jendela konsol
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
