# fx_lot_master.spec
# PyInstaller spec file for FX Lot Master
# Usage:
#   pyinstaller fx_lot_master.spec

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect CustomTkinter themes and assets
ctk_datas = collect_data_files("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
        "yfinance",
        "requests",
        "lxml",
        "lxml.etree",
        "bs4",
        "appdirs",
        "multitasking",
        "frozendict",
        "peewee",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── macOS .app ────────────────────────────────────────────────────────────
if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="FX Lot Master",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="FX Lot Master",
    )
    app = BUNDLE(
        coll,
        name="FX Lot Master.app",
        icon=None,  # replace with path to .icns if available
        bundle_identifier="com.fxlotmaster.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
        },
    )
else:
    # ── Windows .exe (one-dir) ────────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="FX Lot Master",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,  # replace with path to .ico if available
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="FX Lot Master",
    )
