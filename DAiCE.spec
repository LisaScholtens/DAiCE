# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('core', 'core'), ('data', 'data'), ('ui', 'ui')],
    hiddenimports=['numpy', 'PyQt5', 'scipy', 'matplotlib', 'pandas', 'pydantic', 'py_banshee', 'matplotlib.backends.backend_qt5agg', 'PyQt5.Qt', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui'],
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
    [],
    exclude_binaries=True,
    name='DAiCE',
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
    icon=['data\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DAiCE',
)
