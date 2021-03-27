Changelog for PyInstaller 2.x
======================================================

2.1 (2013-09-27)
----------------

- Rewritten manual explaining even very basic topics.
- PyInstaller integration with setuptools (direct installation with easy_install or pip
  from PYPI - https://pypi.python.org/pypi). After installation there will be available
  command 'pyinstaller' for PyInstaller usage.
- (Windows) Alter --version-file resource format to allow unicode support.
- (Windows) Fix running frozen app running from paths containing foreign characters.
- (Windows) Fix running PyInstaller from paths containing foreign characters.
- (OSX) Implement --icon option for the .app bundles.
- (OSX) Add argv emulation for OpenDocument AppleEvent (see manual for details).
- Rename --buildpath to --workpath.
- Created app is put to --distpath.
- All temporary work files are now put to --workpath.
- Add option --clean to remove PyInstaller cache and temporary files.
- Add experimental support for Linux arm.
- Minimum suported Python version is 2.4.
- Add import hooks for docutils, jinja2, sphinx, pytz, idlelib, sqlite3.
- Add import hooks for IPython, Scipy, pygst, Python for .NET.
- Add import hooks for PyQt5, Bacon, raven.
- Fix django import hook to work with Django 1.4.
- Add rthook for twisted, pygst.
- Add rthook for pkg_resource. It fixes the following functions for frozen app
  pkg_resources.resource_stream(), pkg_resources.resource_string().
- Better support for pkg_resources (.egg manipulation) in frozen executables.
- Add option --runtime-hook to allow running custom code from frozen app
  before loading other Python from the frozen app. This is usefull for some
  specialized preprocessing just for the frozen executable. E.g. this
  option can be used to set SIP api v2 for PyQt4.


- Fix runtime option --Wignore.
- Rename utils to lowercase: archieve_viewer.py, bindepend.py, build.py,
  grab_version.py, make_comserver.py, makespec.py, set_version.py.
- (OSX) Fix missing qt_menu.nib in dist directory when using PySide.
- (OSX) Fix bootloader compatibility with Mac OS X 10.5
- (OSX) Search libpython in DYLD_LIBRARY_PATH if libpython cannot be found.
- (OSX) Fix Python library search in virtualenv.
- Environment variable PYTHONHOME is now unset and path to python home
  is set in bootloader by function Py_SetPythonHome().This overrides
  sys.prefix and sys.exec_prefix for frozen application.
- Python library filename (e.g. python27.dll, libpython2.7.so.1.0, etc)
  is embedded to the created exe file. Bootloader is not trying several
  filenames anymore.
- Frozen executables now use PEP-302 import hooks to import frozen modules
  and C extensions. (sys.meta_path)
- Drop old import machinery from iu.py.
- Drop own code to import modules from zip archives (.egg files) in frozen
  executales. Native Python implementation is kept unchanged.
- Drop old crypto code. This feature was never completed.
- Drop bootloader dependency on Python headers for compilation.
- (Windows) Recompile bootloaders with VS2008 to ensure win2k compatibility.
- (Windows) Use 8.3 filenames for homepath/temppath.
- Add prefix LOADER to the debug text from bootloader.
- Allow running PyInstaller programatically.
- Move/Rename some files, code refactoring.
- Add more tests.
- Tilde is in PyInstaller recognized as $HOME variable.


2.0 (2012-08-08)
----------------

- Minimum suported Python version is 2.3.
- (OSX) Add support for Mac OS X 64-bit
- (OSX) Add support Mac OS X 10.7 (Lion) and 10.8 (Mountain Lion).
- (OSX) With argument --windowed PyInstaller creates application bundle (.app)
- automatically.
- Add experimental support for AIX (thanks to Martin Gamwell Dawids).
- Add experimental support for Solaris (thanks to Hywel Richards).
- Add Multipackage function to create a collection of packages to avoid
- library duplication. See documentation for more details.
- New symplified command line interface. Configure.py/Makespec.py/Build.py
- replaced by pyinstaller.py. See documentation for more details.
- Removed cross-building/bundling feature which was never really finished.
- Added option --log-level to all scripts to adjust level of output
  (thanks to Hartmut Goebel).
- rthooks.dat moved to support/rthooks.dat
- Packaged executable now returns the same return-code as the
- unpackaged script (thanks to Brandyn White).
- Add import hook for PyUSB (thanks to Chien-An "Zero" Cho).
- Add import hook for wx.lib.pubsub (thanks to Daniel Hyams).
- Add import hook for pyttsx.
- Improve import hook for Tkinter.
- Improve import hook for PyQt4.
- Improve import hook for win32com.
- Improve support for running PyInstaller in virtualenv.
- Add cli options --additional-hooks-dir and --hidden-import.
- Remove cli options -X, -K, -C, --upx, --tk, --configfile, --skip-configure.
- UPX is used by default if available in the PATH variable.


- Remove compatibility code for old platforms (dos, os2, MacOS 9).
- Use Python logging system for message output (thanks to Hartmut
  Goebel).
- Environment variable MEIPASS2 is accessible as sys._MEIPASS.
- Bootloader now overrides PYTHONHOME and PYTHONPATH.
  PYTHONHOME and PYTHONPATH is set to the value of MEIPASS2 variable.
- Bootloader uses absolute paths.
- (OSX) Drop dependency on otool from Xcode on Mac OSX.
- (OSX) Fix missing qt_menu.nib in dist directory when using PyQt4.
- (OSX) Bootloader does not use DYLD_LIBRARY_PATH on Mac OS X anymore.
  @loader_path is used instead.
- (OSX) Add support to detect .dylib dependencies on Mac OS X containing
  @executable_path, @loader_path and @rpath.
- (OSX) Use macholib to detect dependencies on dynamic libraries.
- Improve test suite.
- Improve source code structure.
- Replace os.system() calls by suprocess module.
- Bundle fake 'site' module with frozen applications to prevent loading
  any user's Python modules from host OS.
- Include runtime hooks (rthooks) in code analysis.
- Source code hosting moved to github:
  https://github.com/pyinstaller/pyinstaller
- Hosting for running tests daily:
  https://jenkins.shiningpanda-ci.com/pyinstaller/


.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
