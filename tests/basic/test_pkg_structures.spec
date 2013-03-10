# -*- mode: python -*-

__testname__ = 'test_pkg_structures'

a = Analysis([__testname__ + '.py'],
        hookspath=['hooks1'])

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__ + '.exe'),
          icon=__testname__+'.ico',
          version=__testname__+'-version.txt',
          debug=0,
          console=1)

coll = COLLECT( exe,
               a.binaries,
               name=os.path.join('dist', __testname__),)
