# -*- mode: python -*-

__testname__ = 'test-matplotlib_i'

if config['target_platform'] == 'win32' and sys.version_info[:2] >= (2, 6):
    manifest = '''<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.VC90.CRT" version="9.0.21022.8" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b"></assemblyIdentity>
    </dependentAssembly>
  </dependency>
</assembly>'''
else:
    manifest = None

a = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'), 
              os.path.join(HOMEPATH,'support', 'useUnicode.py'), 
              __testname__ + '.py'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.' + config['target_platform'], __testname__, 
                            __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=True,
          manifest=manifest )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=os.path.join('dist', __testname__))
