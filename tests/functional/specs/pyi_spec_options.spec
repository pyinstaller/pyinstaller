# -*- mode: python ; coding: utf-8 -*-
import argparse

parser = argparse.ArgumentParser()
optional_dependencies = ["email", "gzip", "pstats"]
parser.add_argument("--optional-dependency", choices=optional_dependencies,
                    action="append", default=[], help="help blah blah blah")
options = parser.parse_args()

source = os.path.join(os.path.dirname(SPECPATH), 'scripts', 'pyi_spec_options.py')

a = Analysis(
    [source],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=options.optional_dependency,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[i for i in optional_dependencies if i not in options.optional_dependency],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pyi_spec_options',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pyi_spec_options",
)
