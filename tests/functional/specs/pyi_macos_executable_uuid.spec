# -*- mode: python ; coding: utf-8 -*-

# First program script built as a POSIX onedir application.
program_script = os.path.join(os.path.dirname(SPECPATH), 'scripts', 'pyi_helloworld.py')

a = Analysis([program_script])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    name='program1_onedir',
    exclude_binaries=True,  # onedir
    console=True,  # console-enabled bootloader
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='program1_onedir',
)

# First program script built as a POSIX onefile application.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=False,  # onefile
    name='program1_onefile',
    console=True,  # console-enabled bootloader
)

# First program script built as an .app bundle.
exe = EXE(
    pyz,
    a.scripts,
    name='program1_onedir_w',
    exclude_binaries=True,  # onedir
    console=False,  # windowed
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='program1_onedir_w',
)
app = BUNDLE(
    coll,
    name='program1_onedir_w.app'
)


# Second program script built as a POSIX onedir application.
# NOTE: second program script is identical to the first one (same file - so the script name matches as well)!
program_script = os.path.join(os.path.dirname(SPECPATH), 'scripts', 'pyi_helloworld.py')

a = Analysis([program_script])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    name='program2_onedir',
    exclude_binaries=True,  # onedir
    console=True,  # console-enabled bootloader
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='program2_onedir',
)

# Second program script built as a POSIX onefile application.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=False,  # onefile
    name='program2_onefile',
    console=True,  # console-enabled bootloader
)


# Third program script built as a POSIX onedir application.
program_script = os.path.join(os.path.dirname(SPECPATH), 'scripts', 'pyi_helloworld2.py')

a = Analysis([program_script])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    name='program3_onedir',
    exclude_binaries=True,  # onedir
    console=True,  # console-enabled bootloader
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='program3_onedir',
)

# Third program script built as a POSIX onefile application.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=False,  # onefile
    name='program3_onefile',
    console=True,  # console-enabled bootloader
)
