# -*- mode: python ; coding: utf-8 -*-
import os

# Запускати з папки bridge: cd bridge; pyinstaller TradeTrackSync.spec
# (у spec немає __file__, тому використовуємо поточну директорію)
SPEC_DIR = os.getcwd()
ICON_PATH = os.path.join(SPEC_DIR, 'icon.ico')

a = Analysis(
    ['main.py'],
    pathex=[SPEC_DIR],
    binaries=[],
    datas=[(ICON_PATH, '.')],
    hiddenimports=['numpy', 'MetaTrader5'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TradeTrackSync',
    icon=ICON_PATH,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
