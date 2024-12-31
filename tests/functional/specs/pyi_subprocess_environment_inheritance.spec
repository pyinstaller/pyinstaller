# -*- mode: python ; coding: utf-8 -*-

# Use a single script to build a pair of identical onedir and a pair of identical onefile executables.
app_src = os.path.join(os.path.dirname(SPECPATH), 'scripts', 'pyi_subprocess_environment_inheritance.py')

debug = False

a = Analysis([app_src])
pyz = PYZ(a.pure)

# First onedir executable
exe_1 = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='onedir_program_1',
    debug=debug,
    console=True,
)
coll_1 = COLLECT(
    exe_1,
    a.binaries,
    a.datas,
    name='onedir_program_1',
)

# Second onedir executable
exe_2 = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='onedir_program_2',
    debug=debug,
    console=True,
)
coll_2 = COLLECT(
    exe_2,
    a.binaries,
    a.datas,
    name='onedir_program_2',
)

# First onefile executable
exe_3 = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='onefile_program_1',
    debug=debug,
    console=True,
)

# Second onefile executable
exe_4 = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='onefile_program_2',
    debug=debug,
    console=True,
)
