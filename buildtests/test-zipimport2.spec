# -*- mode: python -*-

__basename__ = 'zipimport2'
__testname__ = 'test-' + __basename__
__distdir__ = 'dist' + __testname__
import os
if not os.path.isdir(__distdir__):
    os.mkdir(__distdir__)

a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'),
              os.path.join(HOMEPATH,'support/useUnicode.py'),
              os.path.join(HOMEPATH,'support/_pyi_egg_extract.py'),
              __testname__ + '.py'],
             )
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          # funny name to meet runtests.py's schema
          name = '%s%s%s.exe' % (__distdir__, os.sep, __testname__),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
