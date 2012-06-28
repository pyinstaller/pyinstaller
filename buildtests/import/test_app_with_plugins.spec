# -*- mode: python -*-

__testname__ = 'test_app_with_plugins'



a = Analysis([__testname__+'.py'], pathex=[])

TOC_custom = [('static_plugin.py','static_plugin.py','DATA')]

pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__ + '.exe'),
          debug=1,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               TOC_custom,
               name=os.path.join('dist', __testname__),)
