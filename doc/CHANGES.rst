Changelog for PyInstaller
=========================

..
   Define some Sphinx standard roles so they can be used in the README. This
   should not interfer with Sphinx.
.. role:: ref
.. role:: program


3.3 (2017-09-21)
----------------

* **Add Support for Python 3.6!** Many thanks to xiovat! (#2331, #2341)

* New command line options for adding data files (``--datas``, #1990) and
  binaries (``--binaries``, #703)

* Add command line option '--runtime-tmpdir'.

* Bootloaders for Windows are now build using MSVC and statically linked with
  the run-time-library (CRT). This solved a lot of issues related to .dlls
  being incompatible with the ones required by ``python.dll``.

* Bootloaders for GNU/Linux are now officially no LSB binaries. This was
  already the case since release 3.1, but documented the other way round. Also
  the build defaults to non-LSB binaries now. (#2369)

* We improved and stabilized both building the bootloaders and the continuous
  integration tests. See below for details. Many thanks to all who worked on
  this.

* To ease solving issues with packages included wrongly, the html-file with a
  cross-reference is now always generated. It's visual appearance has been
  modernized (#2765).

Incompatible changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Command-line option obsoleted several version ago are not longer handled
  gracefully but raise an error (#2413)

* Installation: PyInstaller removed some internal copies of 3rd-party
  packages. These are now taken from their official releases at PyPI (#2589).
  This results in PyInstaller to no longer can be used from just an unpacked
  archive, but needs to be installed like any Python package. This should
  effect only a few people, e.g. the developers.

* Following :pep:`527`, we only release one source archive now and decided to
  use `.tar.gz` (#2754).

Hooks
~~~~~~~~~~

* New and Updated hooks: accessible_output2 (#2266), ADIOS (#2096), CherryPy
  (#2112), PySide2 (#2471, #2744) (#2472), Sphinx (#2612, 2708) (#2708),
  appdir (#2478), clr (#2048), cryptodome (#2125), cryptography (#2013), dclab
  (#2657), django (#2037), django migrations (#1795), django.contrib (#2336),
  google.cloud, google.cloud.storage, gstreamer (#2603), imageio (#2696),
  langcodes (#2682), libaudioverse (#2709), mpl_toolkits (#2400), numba,
  llvmlite (#2113), openpyxl (#2066), pylint, pymssql, pyopencl, pyproj
  (#2677), pytest (#2119), qtawesome (#2617), redmine, requests (#2334),
  setuptools, setuptools (#2565), shapely (#2569), sound_lib (#2267),
  sysconfig, uniseg (#2683), urllib3, wx.rc (#2295),

  * numpy: Look for .dylib libraries, too ( (#2544), support numpy MKL builds
    (#1881, #2111)

  * osgeo: Add conda specific places to check for auxiliary data (#2401)

  * QT and related

    - Add hooks for PySide2
    - Eliminate run-time hook by placing files in the correct directory
    - Fix path in homebrew for searching for qmake (#2354)
    - Repair Qt dll location  (#2403)
    - Bundle PyQT 5.7 DLLs (#2152)
    - PyQt5: Return qml plugin path including subdirectory (#2694)
    - Fix hooks for PyQt5.QtQuick (#2743)
    - PyQt5.QtWebEngineWidgets: Include files needed by QWebEngine

  * GKT+ and related

    - Fix Gir file path on windows.
    - Fix unnecessary file search & generation when GI's typelib is exists
    - gi: change gir search path when running from a virtualenv
    - gi: package gdk-pixbuf in osx codesign agnostic dir
    - gi: rewrite the GdkPixbuf loader cache at runtime on Linux
    - gi: support onefile mode for GdkPixbuf
    - gi: support using gdk-pixbuf-query-loaders-64 when present
    - gi: GIR files are only required on OSX
    - gio: copy the mime.cache also
    - Fix hooks for PyGObject on windows platform (#2306)

* Fixed hooks: botocore (#2384), clr (#1801), gstreamer (#2417), h5py
  (#2686), pylint, Tix data files (#1660), usb.core (#2088), win32com on
  non-windows-systems (#2479)

* Fix ``multiprocess`` spawn mode on POSIX OSs (#2322, #2505, #2759, #2795).

Bootloader
~~~~~~~~~~~~~~

* Add `tempdir` option to control where bootloader will extract files (#2221)
* (Windows) in releases posted on PyPI requires msvcr*.dll (#2343)
* Fix unsafe string manipulation, resource and memory leaks. Thanks to Vito
  Kortbeek (#2489, #2502, #2503)
* Remove a left-over use of ``getenv()``
* Set proper LISTEN_PID (set by `systemd`) in child process (#2345)
* Adds PID to bootloader log messages (#2466, #2480)

* (Windows) Use _wputenv_s() instead of ``SetEnvironmentVariableW()``
* (Windows) Enhance error messages (#1431)
* (Windows) Add workaround for a Python 3 issue
  http://bugs.python.org/issue29778 (#2496, #2844)

* (OS X): Use single process for --onedir mode (#2616, #2618)

* (GNU/Linux) Compile bootloaders with --no-lsb by default (#2369)
* (GNU/Linux) Fix: linux64 bootloader requires glibc 2.14 (#2160)
* (GNU/Linux) set_dynamic_library_path change breaks plugin library use
  (#625)

Bootloader build
~~~~~~~~~~~~~~~~~~~

The bootloader build was largely overhauled. In the wscript, the build no
longer depends on the Python interpreter's bit-size, but on the compiler. We
have a machine for building bootloaders for Windows and cross-building for
OS X. Thus all mainteriner are now able to build the bootloaders for all
supported platforms.

* Add "official" build-script.

* (GNU/Linux) Make --no-lsb the default, add option --lsb.
  
* Largely overhauled Vagrantfile:

    - Make Darwin bootloaders build in OS X box (unused)
    - Make Windows bootloaders build using MSVC
    - Allow specifying cross-target on linux64.
    - Enable cross-building for OS X.
    - Enable cross-building for Windows (unused)
    - Add box for building osxcross.

* Largely overhauled wscript:

    - Remove options --target-cpu.
    - Use compiler's target arch, not Python's.
    - Major overhaul of the script
    - Build zlib if required, not if "on windows".
    - Remove obsolete warnings.
    - Update Solaris, AIX and HPUX support.
    - Add flags for 'strip' tool in AIX platform.
    - Don't set POSIX / SUS version defines.

* (GNU/Linux) for 64-bit arm/aarch ignore the :program:`gcc` flag ``-m64``
  (#2801).
  
Module loader
~~~~~~~~~~~~~~~~~~~~~~

* Implement PEP-451 ModuleSpec type import system (#2377)
* Fix: Import not thread-save? (#2010, #2371)

PyInstaller Core
~~~~~~~~~~~~~~~~~~~~~~~

* Analyze: Check Python version when testing whether to rebuild.
* Analyze: Don't fail on syntax error in modules, simply ignore them.
* Better error message when `datas` are not found. (#2308)
* Building: OSX: Use unicode literals when creating Info.plist XML
* Building: Don't fail if "datas" filename contain glob special characters.
  (#2314)
* Building: Read runtime-tmpdir from .spec-file.
* Building: Update a comment.
* building: warn users if bincache gets corrupted. (#2614)
* Cli-utils: Remove graceful handling of obsolete command line options.
* Configure: Create new parent-dir when moving old cache-dir. (#2679)
* Depend: Include vcruntime140.dll on Windows. (#2487)
* Depend: print nice error message if analyzed script has syntax error.
* Depend: When scanning for ctypes libs remove non-basename binaries.
* Enhance run-time error message on ctypes import error.
* Fix #2585: py2 non-unicode sys.path been tempted by os.path.abspath().
  (#2585)
* Fix crash if extension module has hidden import to ctypes. (#2492)
* Fix handling of obsolete command line options. (#2411)
* Fix versioninfo.py breakage on Python 3.x (#2623)
* Fix: "Unicode-objects must be encoded before hashing" (#2124)
* Fix: UnicodeDecodeError - collect_data_files does not return filenames as
  unicode (#1604)
* Remove graceful handling of obsolete command line options. (#2413)
* Make grab version more polite on non-windows (#2054)
* Make utils/win32/versioninfo.py round trip the version info correctly.
* Makespec: Fix version number processing for PyCrypto. (#2476)
* Optimizations and refactoring to modulegraph and scanning for ctypes
  dependencies.
* pyinstaller should not crash when hitting an encoding error in source code
  (#2212)
* Remove destination for COLLECT and EXE prior to copying it (#2701)
* Remove uninformative traceback when adding not found data files (#2346)
* threading bug while processing imports (#2010)
* utils/hooks: Add logging to collect_data_files.

* (win32) Support using pypiwin32 or pywin32-ctypes (#2602)
* (win32) Use os.path.normpath to ensure that system libs are excluded.
* (win32) Look for libpython%.%.dll in Windows MSYS2 (#2571)
* (win32) Make versioninfo.py round trip the version info correctly (#2599)
* (win32) Ensure that pywin32 isn't imported before check_requirements is
  called

* (win32) pyi-grab_version and --version-file not working? (#1347)
* (win32) Close PE() object to avoid mmap memory leak (#2026)
* (win32) Fix: ProductVersion in windows version info doesn't show in some
  cases (#846)
* (win32) Fix multi-byte path bootloader import issue with python2 (#2585)
* (win32) Forward DYLD_LIBRARY_PATH through `arch` command. (#2035)
* (win32) Add ``vcruntime140.dll`` to_win_includes for Python 3.5 an 3.6
  (#2487)

* (OS X) Add libpython%d.%dm.dylib to Darwin (is_darwin) PYDYLIB_NAMES.
  (#1971)
* (OS X) macOS bundle Info.plist should be in UTF-8 (#2615)
* (OS X) multiprocessing spawn in python 3 does not work on macOS (#2322)
* (OS X) Pyinstaller not able to find path (@rpath) of dynamic library (#1514)

* Modulegraph

  - Align with upstream version 0.13.
  - Add the upstream test-suite
  - Warn on syntax error and unicode error. (#2430)
  - Implement ``enumerate_instructions()`` (#2720)
  - Switch byte-code analysis to use `Instruction` (like dis3 does) (#2423)
  - Log warning on unicode error instead of only a debug message (#2418)
  - Use standard logging for messages. (#2433)
  - Fix to reimport failed SWIG C modules (1522, #2578).

* Included 3rd-party libraries

  - Remove bundled ``pefile`` and ``macholib``, use the releases from PyPI.
    (#1920, #2689)
  - altgraph: Update to altgraph 0.13, add upstream test-suite.

Utilities
~~~~~~~~~~~~~~~

* :program:`grab_version.py`: Display a friendly error message when utility
  fails (#859, #2792).

    
Test-suite and Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Rearrange requirements files.
* Pin required versions – now updated using pyup (#2745)
* Hide useless trace-backs of helper-functions.
* Add a test for PyQt5.QtQuick.
* Add functional tests for PySide2
* Add test for new feature --runtime-tmpdir.
* Fix regression-test for #2492.
* unit: Add test-cases for PyiModuleGraph.
* unit/altgraph: Bringing in upstream altgraph test-suite.
* unit/modulegraph: Bringing in the modulegraph test-suite.

* Continuous Integration

  - Lots of enhancements to the CI tests to make them more stabile and
    reliable.
  - Pin required versions – now updated using pyup (#2745)
  - OS X is now tested along with GNU/Linux at Travis CI (#2508)
  - Travis: Use stages (#2753)
  - appveyor: Save cache on failure (#2690)
  - appveyor: Verify built bootloaders have the expected arch.

Documentation
~~~~~~~~~~~~~~~~~~~

* Add information how to donate (#2755, #2772).
* Add how to install the development version using pip.
* Fix installation instructions for development version. (#2761)
* Better examples for hidden imports.
* Clarify and fix "Adding Data Files" and "Adding Binary Files". (#2482)
* Document new command line option '--runtime-tmpdir'.
* pyinstaller works on powerpc linux, big endian arch (#2000)
* Largely rewrite section "Building the Bootloader", update from the wiki
  page.
* Describe building LSB-compliant bootloader as (now) special case.
* help2rst: Add cross-reference labels for option-headers.
* Enable sphinx.ext.intersphinx and links to our website.
* Sphinx should not "adjust" display of command line documentation (#2217)

Known Issues
~~~~~~~~~~~~~~~~~~

* Data-files from wheels, unzipped eggs or not ad egg at all are not included
  automatically. This can be worked around using a hook-file, but may not
  suffice when using ``--onefile`` and something like `python-daemon`.

* The multipackage (MERGE) feature (#1527) is currently broken.

* (OSX) Support for OpenDocument events (#1309) is broken.

* (Windows) With Python 2.7 the frozen application may not run if the
  user-name (more specifically ``%TEMPDIR%``) includes some Unicode
  characters. This does not happen with all Unicode characters, but only some
  and seems to be a windows bug. As a work-around please upgrade to Python 3
  (#2754, #2767).

* (Windows) For Python >= 3.5 targeting *Windows < 10*, the developer needs to
  take special care to include the Visual C++ run-time .dlls. Please see the
  section :ref:`Platform-specific Notes <Platform-specific Notes - Windows>`
  in the manual. (#1566)

* For Python 3.3, imports are not thread-safe (#2371#). Since Python 3.3 is
  end of live at 2017-09-29, we are not going to fix this.

  
3.2.1 (2017-01-15)
------------------

- New, updated and fixed hooks: botocore (#2094), gi (#2347), jira (#2222),
  PyQt5.QtWebEngineWidgets (#2269), skimage (#2195, 2225), sphinx (#2323,)
  xsge_gui (#2251).

Fixed the following issues:

- Don't fail if working directory already exists (#1994)
- Avoid encoding errors in main script (#1976)
- Fix hasher digest bytes not str (#2229, #2230)

- (Windows) Fix additional dependency on the msvcrt10.dll (#1974)
- (Windows) Correctly decode a bytes object produced by pefile (#1981)
- (Windows) Package ``pefile`` with pyinstaller.  This partially
  undoes some changes in 3.2 in which the packaged pefiles were
  removed to use the pypi version instead.  The pypi version was
  considerably slower in some applications, and still has a couple
  of small issues on PY3. (#1920)

- (OS X) PyQt5 packaging issues on MacOS (#1874)
- (OS X) Replace run-time search path keyword (#1965)
- (OS X) (Re-) add argv emulation for OSX, 64-bit (#2219)
- (OS X) use decode("utf-8") to convert bytes in getImports_macholib() (#1973)

- (Bootloader) fix segfaults (#2176)
- (setup.py) pass option --no-lsb on GNU/Linux only (#1975)

- Updates and fixes in documentation, manuals, et al. (#1986, 2002, #2153,
  #2227, #2231)


3.2 (2016-05-03)
----------------

- Even the "main" script is now byte-compiled (#1847, #1856)
- The manual is on readthedocs.io now (#1578)
- On installation try to compile the bootloader if there is none for
  the current plattform (#1377)

- (Unix) Use ``objcopy`` to create a valid ELF file (#1812, #1831)
- (Linux): Compile with ``_FORTIFY_SOURCE`` (#1820)

- New, updated and fixed hooks: CherryPy (#1860), Cryptography (#1425,
  #1861), enchant (1562), gi.repository.GdkPixbuf (#1843), gst
  (#1963), Lib2to3 (#1768), PyQt4, PyQt5, PySide (#1783, #1897,
  #1887), SciPy (#1908, #1909), sphinx (#1911, #1912), sqlalchemy
  (#1951), traitlets wx.lib.pubsub (#1837, #1838),

- For windowed mode add ``isatty()`` for our dummy NullWriter (#1883)
- Suppress "Failed to execute script" in case of SystemExit (#1869)
- Do not apply Upx compressor for bootloader files (#1863)
- Fix absolute path for lib used via ctypes (#1934)
- (OSX) Fix binary cache on NFS (#1573, #1849)
- (Windows) Fix message in grab_version (#1923)
- (Windows) Fix wrong icon paramter in Windows example (#1764)
- (Windows) Fix win32 unicode handling (#1878)
- (Windows) Fix unnecessary rebuilds caused by rebuilding winmanifest
  (#1933)
- (Cygwin) Fix finding the Python library for Cygwin 64-bit (#1307,
  #1810, #1811)
- (OSX) Fix compilation issue (#1882)
- (Windows) No longer bundle ``pefile``, use package from pypi for windows
  (#1357)
- (Windows) Provide a more robust means of executing a Python script
- AIX fixes.

- Update waf to version 1.8.20 (#1868)
- Fix excludedimports, more predictable order how hooks are applied
  #1651
- Internal impovements and code clean-up (#1754, #1760, #1794, #1858,
  #1862, #1887, #1907, #1913)
- Clean-ups fixes and improvements for the test suite

**Known Issues**

- Apps built with Windows 10 and Python 3.5 may not run on Windows versions
  earlier than 10 (#1566).
- The multipackage (MERGE) feature (#1527) is currently broken.
- (OSX) Support for OpenDocument events (#1309) is broken.


3.1.1 (2016-01-31)
------------------

Fixed the following issues:

- Fix problems with setuptools 19.4 (#1772, #1773, #1790, #1791)
- 3.1 does not collect certain direct imports (#1780)
- Git reports wrong version even if on unchanged release (#1778)
- Don't resolve symlinks in modulegraph.py (#1750, #1755)
- ShortFileName not returned in win32 util (#1799)


3.1 (2016-01-09)
----------------

- Support reproducible builds (#490, #1434, #1582, #1590).
- Strip leading parts of paths in compiled code objects (#1059, #1302,
  #1724).

- With ``--log-level=DEBUG``, a dependency graph-file is emitted in
  the build-directory.

- Allow running pyinstaller as user `root`. By popular demand, see
  e.g. #1564, #1459, #1081.

- New Hooks: botocore, boto3, distorm3, GObject, GI (G Introspection),
  GStreamer, GEvent, kivy, lxml.isoschematron, pubsub.core,
  PyQt5.QtMultimedia, scipy.linalg, shelve.
- Fixed or Updated Hooks: astroid, django, jsonschema logilab, PyQt4,
  PyQt5, skimage, sklearn.
- Add option ``--hiddenimport`` as an alias for ``--hidden-import``.

- (OSX): Fix issues with ``st_flags`` (#1650).
- (OSX) Remove warning message about 32bit compatibility (#1586).
- (Linux) The cache is now stored in ``$XDG_CACHE_HOME/pyinstaller``
  instead of ``$XDG_DATA_HOME`` - the cache is moved automatically (#1118).
- Documentation updates, e.g. about reproducible builds

- Put back full text of GPL license into COPYING.txt.
- Fix crashes when looking for ctypes DLLs (#1608, #1609, #1620).
- Fix: Imports in byte-code not found if code contains a function (#1581).
- Fix recursion into bytes-code when scanning for ctypes (#1620).
- Fix PyCrypto modules to work with crypto feature (``--key`` option)
  (#1663).
- Fix problems with ``excludedimports`` in some hook excluding the
  named modules even if used elswhere (#1584, #1600).
- Fix freezing of pip 7.1.2 (#1699).
- FreeBSD and Solaris fixes.

- Search for ``ldconfig`` in $PATH first (#1659)
- Deny processing outdated package ``_xmlplus``.

- Improvements to the test-suite, testing infrastructure and
  continuous integration.
- For non-release builds, the exact git revision is not used.
- Internal code refactoring.
- Enhancements and clean-ups to the hooks API - only relevant for hook
  authors. See the manual for details. E.g:

  - Removed ``attrs`` in hooks - they were not used anymore anyway.
  - Change ``add/del_import()`` to accept arbitrary number of module
    names.
  - New hook utility function ``copy_metadata()``.

**Known Issues**

- Apps built with Windows 10 and Python 3.5 may not run on Windows versions
  earlier than 10 (#1566).
- The multipackage (MERGE) feature (#1527) is currently broken.
- (OSX) Support for OpenDocument events (#1309) is broken.



3.0 (2015-10-04)
----------------

- Python 3 support (3.3 / 3.4 / 3.5).
- Remove support for Python 2.6 and lower.
- Full unicode support in the bootloader (#824, #1224, #1323, #1340, #1396)

  - (Windows) Python 2.7 apps can now run from paths with non-ASCII characters
  - (Windows) Python 2.7 onefile apps can now run for users whose usernames
    contain non-ASCII characters
  - Fix ``sys.getfilesystemencoding()`` to return correct values (#446, #885).

- (OSX) Executables built with PyInstaller under OS X can now be digitally
  signed.
- (OSX) 32bit precompiled bootloader no longer distributed, only 64bit.
- (Windows) for 32bit bootloader enable flag LARGEADDRESSAWARE that allows
  to use 4GB of RAM.
- New hooks: amazon-product-api, appy, certifi, countrycode, cryptography, gi,
  httplib2, jsonschema, keyring, lensfunpy, mpl_toolkits.basemap, ncclient,
  netCDF4, OpenCV, osgeo, patsy, PsychoPy, pycountry, pycparser, PyExcelerate,
  PyGobject, pymssql, PyNaCl, PySiDe.QtCore, PySide.QtGui, rawpy, requests,
  scapy, scipy, six, SpeechRecognition, u1db, weasyprint, Xlib.
- Hook fixes: babel, ctypes, django, IPython, pint, PyEnchant, Pygments, PyQt5,
  PySide, pyusb, sphinx, sqlalchemy, tkinter, wxPython.
- Add support for automatically including data files from eggs.
- Add support for directory eggs support.
- Add support for all kind of namespace packages e.g.
  ``zope.interface``, PEP302 (#502, #615, #665, #1346).
- Add support for ``pkgutil.extend_path()``.
- New option ``--key`` to obfuscate the Python bytecode.
- New option ``--exclude-module`` to ignore a specific module or package.
- (Windows) New option ``--uac-admin`` to request admin permissions
  before starting the app.
- (Windows) New option ``--uac-uiaccess`` allows an elevated
  application to work with Remote Desktop.
- (Windows) New options for Side-by-side Assembly searching:

  - ``--win-private-assemblies`` bundled Shared Assemblies into the
    application will be changed into Private Assemblies
  - ``--win-no-prefer-redirects`` while searching for Assemblies
    PyInstaller will prefer not to follow policies that redirect to
    newer versions.

- (OSX) New option ``--osx-bundle-identifier`` to set .app bundle identifier.
- (Windows) Remove old COM server support.
- Allow override PyInstaller default config directory by environment
  variable ``PYINSTALLER_CONFIG_DIR``.
- Add FreeBSD support.
- AIX fixes.
- Solaris fixes.
- Use library modulegraph for module dependency analysis.
- Bootloader debug messages ``LOADER: ...`` printed to stderr.
- PyInstaller no longer extends ``sys.path`` and bundled 3rd-party
  libraries do not interfere with their other versions.
- Enhancemants to ``Analysis()``:

  - New arguments ``excludedimports`` to exclude Python modules in
    import hooks.
  - New argument ``binaries`` to bundle dynamic libraries in `.spec`
    file and in import hooks.
  - New argument ``datas`` to bundle additional data files in `.spec`
    file and in import hooks.

- A lot of internal code refactoring.
- Test suite migrated to pytest framework.
- Improved testing infrastructure with continuous integration (Travis - Linux,
  Appveyor - Windows)
- Wiki and bug tracker migrated to github.


**Known Issues**

- Apps built with Windows 10 and Python 3.5 may not run on Windows versions
  earlier than 10 (#1566).
- The multipackage (MERGE) feature (#1527) is currenty broken.
- (OSX) Support for OpenDocument events (#1309) is broken.


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


1.5.1 (2011-08-01)
------------------

- New default PyInstaller icon for generated executables on Windows.
- Add support for Python built with --enable-shared on Mac OSX.
- Add requirements section to documentation.


- Documentation is now generated by rst2html and rst2pdf.
- Fix wrong path separators for bootloader-file on Windows
- Add workaround for incorrect platform.system() on some Python Windows
  installation where this function returns 'Microsoft' instead 'Windows'.
- Fix --windowed option for Mac OSX where a console executable was
  created every time even with this option.
- Mention dependency on otool, ldd and objdump in documentation.
- Fix typo preventing detection of DLL libraries loaded by ctypes module.


1.5 (2011-05-05)
----------------

- Full support for Python 2.7.
- Full support for Python 2.6 on Windows. No manual redistribution
  of DLLs, CRT, manifest, etc. is required: PyInstaller is able to
  bundle all required dependencies (thanks to Florian Hoech).
- Added support for Windows 64-bit (thanks to Martin Zibricky).
- Added binary bootloaders for Linux (32-bit and 64-bit, using LSB),
  and Darwin (32-bit). This means that PyInstaller users on this
  platform don't need to compile the bootloader themselves anymore
  (thanks to Martin Zibricky and Lorenzo Mancini).


- Rewritten the build system for the bootloader using waf (thanks
  to Martin Zibricky)
- Correctly detect Python unified binary under Mac OSX, and bail out
  if the unsupported 64-bit version is used (thanks to Nathan Weston).
- Fix TkInter support under Mac OSX (thanks to Lorenzo Mancini).
- Improve bundle creation under Mac OSX and correctly support also
  one-dir builds within bundles (thanks to Lorenzo Mancini).
- Fix spurious KeyError when using dbhash
- Fix import of nested packages made from Pyrex-generated files.
- PyInstaller is now able to follow dependencies of binary extensions
  (.pyd/.so) compressed within .egg-files.
- Add import hook for PyTables.
- Add missing import hook for QtWebKit.
- Add import hook for pywinauto.
- Add import hook for reportlab (thanks Nevar).
- Improve matplotlib import hook (for Mac OSX).
- Improve Django import hooks.
- Improve compatibility across multiple Linux distributions by
  being more careful on which libraries are included/excluded in
  the package.
- Improve compatibility with older Python versions (Python 2.2+).
- Fix double-bouncing-icon bug on Mac OSX. Now windowed applications
  correctly start on Mac OSX showing a single bouncing icon.
- Fix weird "missing symbol" errors under Mac OSX (thanks to Isaac
  Wagner).


1.4 (2010-03-22)
----------------

- Fully support up to Python 2.6 on Linux/Mac and Python 2.5
  on Windows.
- Preliminar Mac OSX support: both one-file and one-dir is supported;
  for non-console applications, a bundle can be created. Thanks
  to many people that worked on this across several months (Daniele
  Zannotti, Matteo Bertini, Lorenzo Mancini).
- Improved Linux support: generated executables are fatter but now
  should now run on many different Linux distributions (thanks to David
  Mugnai).
- Add support for specifying data files in import hooks. PyInstaller
  can now automatically bundle all data files or plugins required
  for a certain 3rd-party package.
- Add intelligent support for ctypes: PyInstaller is now able to
  track all places in the source code where ctypes is used and
  automatically bundle dynamic libraries accessed through ctypes.
  (Thanks to Lorenzo Mancini for submitting this). This is very
  useful when using ctypes with custom-made dynamic libraries.
- Executables built with PyInstaller under Windows can now be digitally
  signed.
- Add support for absolute imports in Python 2.5+ (thanks to Arve
  Knudsen).
- Add support for relative imports in Python 2.5+.
- Add support for cross-compilation: PyInstaller is now able to
  build Windows executables when running under Linux. See documentation
  for more details.
- Add support for .egg files: PyInstaller is now able to look for
  dependencies within .egg files, bundle them and make them available
  at runtime with all the standard features (entry-points, etc.).
- Add partial support for .egg directories: PyInstaller will treat them
  as normal packages and thus it will not bundle metadata.
- Under Linux/Mac, it is now possible to build an executable even when
  a system packages does not have .pyc or .pyo files available and the
  system-directory can be written only by root. PyInstaller will in
  fact generate the required .pyc/.pyo files on-the-fly within a
  build-temporary directory.
- Add automatic import hooks for many third-party packages, including:

  - PyQt4 (thanks to Pascal Veret), with complete plugin support.
  - pyodbc (thanks to Don Dwiggins)
  - cElementTree (both native version and Python 2.5 version)
  - lxml
  - SQLAlchemy (thanks to Greg Copeland)
  - email in Python 2.5 (though it does not support the old-style
    Python 2.4 syntax with Python 2.5)
  - gadfly
  - PyQWt5
  - mako
  - Improved PyGTK (thanks to Marco Bonifazi and foxx).
  - paste (thanks to Jamie Kirkpatrick)
  - matplotlib

- Add fix for the very annoying "MSVCRT71 could not be extracted" bug,
  which was caused by the DLL being packaged twice (thanks to Idris
  Aykun).
- Removed C++-style comments from the bootloader for compatibility
  with the AIX compiler.
- Fix support for .py files with DOS line endings under Linux (fixes
  PyOpenGL).
- Fix support for PIL when imported without top-level package ("import
  Image").
- Fix PyXML import hook under NT (thanks to Lorenzo Mancini)
- Fixed problem with PyInstaller picking up the wrong copy of optparse.
- Improve correctness of the binary cache of UPX'd/strip'd files. This
  fixes problems when switching between multiple versions of the
  same third-party library (like e.g. wxPython allows to do).
- Fix a stupid bug with modules importing optparse (under Linux) (thanks
  to Louai Al-Khanji).
- Under Python 2.4+, if an exception is raised while importing a module
  inside a package, the module is now removed from the parent's
  namespace (to match the behaviour of Python itself).
- Fix random race-condition at startup of one-file packages, that was
  causing this exception to be generated: "PYZ entry 'encodings' (0j)
  is not a valid code object".
- Fix problem when having unicode strings among path elements.
- Fix random exception ("bad file descriptor") with "prints" in non-console
  mode (actually a pythonw "bug" that's fixed in Python 3.0).
- Sometimes the temporary directory did not get removed upon program
  exit, when running on Linux.
- Fixed random segfaults at startup on 64-bit platforms (like x86-64).


1.3 (2006-12-20)
----------------

- Fix bug with user-provided icons disappearing from built executables
  when these were compressed with UPX.
- Fix problems with packaging of applications using PIL (that was broken
  because of a bug in Python's import machinery, in recent Python
  versions). Also add a workaround including Tcl/Tk with PIL unless
  ImageTk is imported.
- (Windows) When used under Windows XP, packaged programs now have
  the correct look & feel and follow user's themes (thanks to the manifest
  file being linked within the generated executable). This is especially
  useful for applications using wxPython.
- Fix a buffer overrun in the bootloader (which could lead to a crash)
  when the built executable is run from within a deep directory (more than
  70-80 characters in the pathname).
- Bootstrap modules are now compressed in the executable (so that they
  are not visible in plaintext by just looking at it with a hex editor).
- Fixed a regression introduced in 1.1: under Linux, the bootloader does
  not depend on libpythonX.X.so anymore.


1.2 (2006-06-29)
----------------

- Fix a crash when invoking UPX with certain kinds of builds.
- Fix icon support by re-adding a resource section in the bootloader
  executable.


1.1 (2006-02-13)
----------------

- (Windows) Make single-file packages not depend on MSVCRT71.DLL anymore,
  even under Python 2.4. You can eventually ship your programs really as
  single-file executables, even when using the newest Python version!
- Fix problem with incorrect python path detection. Now using helpers from
  distutils.
- Fix problem with rare encodings introduced in newer Python versions: now all
  the encodings are automatically found and included, so this problem should
  be gone forever.
- Fix building of COM servers (was broken in 1.0 because of the new build
  system).
- Mimic Python 2.4 behaviour with broken imports: sys.modules is cleaned up
  afterwise. This allows to package SQLObject applications under Windows
  with Python 2.4 and above.
- Add import hook for the following packages:

  - GTK
  - PyOpenGL (tested 2.0.1.09)
  - dsnpython (tested 1.3.4)
  - KInterasDB (courtesy of Eugene Prigorodov)

- Fix packaging of code using "time.strptime" under Python 2.3+.
- (Linux) Ignore linux-gate.so while calculating dependencies (fix provided
  by Vikram Aggarwal).
- (Windows) With Python 2.4, setup UPX properly so to be able to compress
  binaries generated with Visual Studio .NET 2003 (such as most of the
  extensions). UPX 1.92+ is needed for this.


1.0 (2005-09-19) with respect to McMillan's Python Installer 5b5
----------------------------------------------------------------

- Add support for Python 2.3 (fix packaging of codecs).
- Add support for Python 2.4 (under Windows, needed to recompiled the
  bootloader with a different compiler version).
- Fix support for Python 1.5.2, should be fully functional now (required
  to rewrite some parts of the string module for the bootloader).
- Fix a rare bug in extracting the dependencies of a DLL (bug in PE header
  parser).
- Fix packaging of PyQt programs (needed an import hook for a hidden import).
- Fix imports calculation for modules using the "from __init__ import" syntax.
- Fix a packaging bug when a module was being import both through binary
  dependency and direct import.


- Restyle documentation (now using docutils and reStructuredText).
- New Windows build system for automatic compilations of bootloader in all
  the required flavours (using Scons)

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
