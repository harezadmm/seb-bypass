#!/usr/bin/env python3
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: SEB Config Bypass Studio.

Build macOS:   pyinstaller --clean seb_bypass_gui.spec
Build Windows: pyinstaller --clean seb_bypass_gui.spec
"""
import os
import sys

BLOCK_CIPHER = None
block_cipher = None

HERE = os.path.abspath(os.path.dirname(SPEC))  # noqa: F821
# script sumber ada satu level di atas folder build/
SRCDIR = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(SRCDIR, "seb_bypass_gui.py")
if not os.path.isfile(SCRIPT):
    SCRIPT = os.path.join(HERE, "seb_bypass_gui.py")
ICON = os.path.join(HERE, "assets", "sebstudio.icns")
if sys.platform.startswith("win"):
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
              "test", "unittest", "pydoc", "email", "http", "xmlrpc"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SEB Config Bypass Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # aplikasi GUI: tanpa jendela konsol
    disable_windowed_traceback=False,
    argv_emulation=True,    # macOS: drag & drop file .seb ke icon
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SEB Config Bypass Studio",
)

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="SEB Config Bypass Studio.app",
        icon=ICON,
        bundle_identifier="org.harezadmm.sebconfigbypassstudio",
        info_plist={
            "CFBundleName": "SEB Config Bypass Studio",
            "CFBundleDisplayName": "SEB Config Bypass Studio",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.developer-tools",
            "NSRequiresAquaSystemAppearance": False,
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "SEB Config",
                    "CFBundleTypeExtensions": ["seb"],
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                }
            ],
        },
    )
