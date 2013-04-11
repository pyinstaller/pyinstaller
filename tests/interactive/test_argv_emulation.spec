# -*- mode: python -*-
a = Analysis(['test_argv_emulation.py'],
             pathex=[],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.darwin/TestArgvEmu', 'TestArgvEmu'),
          debug=True,
          strip=None,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name=os.path.join('dist', 'TestArgvEmu'))
app = BUNDLE(coll,
             name=os.path.join('dist', 'TestArgvEmu.app'))
