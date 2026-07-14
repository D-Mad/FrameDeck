# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

datas = []
for root, dirs, files in os.walk("resources"):
    dirs[:] = [name for name in dirs if name not in {"__pycache__", "source"}]
    destination = os.path.join("resources", os.path.relpath(root, "resources"))
    for filename in files:
        if not filename.endswith((".pyc", ".pyo")):
            datas.append((os.path.join(root, filename), destination))
datas += collect_data_files("qdarktheme")

binaries = []
binaries += collect_dynamic_libs("OpenImageIO")
binaries += collect_dynamic_libs("PyOpenColorIO")
binaries += collect_dynamic_libs("av")

hiddenimports = collect_submodules("qdarktheme")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FrameDeck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FrameDeck",
)
