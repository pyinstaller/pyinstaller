# -*- mode: python -*-
a = Analysis(['test_site.py'],
             pathex=['/home/martin/Work/pyinstaller/gitrepo/buildtests/import'],
             hiddenimports=['encodings'],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.linux2/test_site', 'test_site'),
          debug=True,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name=os.path.join('dist', 'test_site'))
