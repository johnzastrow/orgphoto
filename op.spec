# -*- mode: python ; coding: utf-8 -*-
<<<<<<< HEAD:op/op.spec


block_cipher = None


a = Analysis(
    ['photocopy.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
=======
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('hachoir')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\br8kw\\Github\\orgphoto\\op.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
>>>>>>> 46d4cb678b39c2103b1072c45d49902c22447513:op.spec

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
<<<<<<< HEAD:op/op.spec
    a.zipfiles,
    a.datas,
    [],
    name='photocopy',
=======
    a.datas,
    [],
    name='op',
>>>>>>> 46d4cb678b39c2103b1072c45d49902c22447513:op.spec
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
<<<<<<< HEAD:op/op.spec
=======
    icon=['C:\\Users\\br8kw\\Github\\orgphoto\\doc\\favicon.ico'],
>>>>>>> 46d4cb678b39c2103b1072c45d49902c22447513:op.spec
)
