# -*- mode: python ; coding: utf-8 -*-
import argparse

# Explicitly set the program name to what the test expects to find in the output (i.e., `pyi_spec_options.spec`).
# Starting with python 3.14, the automatically-inferred program name becomes `python -m pytest` when `pytest` is
# launched as a module. See: https://github.com/python/cpython/commit/04bfea2d261bced371cbd64931fe2a8f64984793
parser = argparse.ArgumentParser(prog='pyi_spec_options.spec')
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
