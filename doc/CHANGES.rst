Changelog for PyInstaller
=========================

..
   Define some Sphinx standard roles so they can be used in the README. This
   should not interfer with Sphinx.
.. role:: ref
.. role:: program


3.4 (unreleased)
----------------

- Nothing changed yet.


3.3.1 (2017-12-13)
------------------

Hooks
~~~~~~~~~~

* Fix imports in hooks accessible_output and sound_lib (#2860).
* Fix ImportError for sysconfig for 3.5.4 Conda (#3105, #3106).
* Fix shapely hook for conda environments on Windows (#2838).
* Add hook for unidecode.

Bootloader
~~~~~~~~~~~~~~

* (Windows) Pre-build bootloaders (and custom-build ones using MSVC) can be
  used on Windows XP again. Set minimum target OS to XP (#2974).

Bootloader build
~~~~~~~~~~~~~~~~~~~

* Fix build for FreeBSD (#2861, #2862).

PyInstaller Core
~~~~~~~~~~~~~~~~~~~~~~~

* Usage: Add help-message clarifying use of options when a spec-file is
  provided (#3039).

* Add printing infos on UnicodeDecodeError in exec_command(_all).
* (win32) Issue an error message on errors loading the icon file (#2039).
* (aarch64) Use correct bootloader for 64-bit ARM (#2873).
* (OS X) Fix replacement of run-time search path keywords (``@…`` ) (#3100).

* Modulegraph

  * Fix recursion too deep errors cause by reimporting SWIG-like modules
    (#2911, #3040, #3061).
  * Keep order of imported identifiers.


Test-suite and Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* In Continuous Integration tests: Enable flake8-diff linting. This will
  refuse all changed lines not following PEP 8.

* Enable parallel testing on Windows,
* Update requirements.
* Add more test cases for modulegraph.
* Fix a test-case for order of module import.

* Add test-cases to check scripts do not share the same global vars (see
  :ref:`v3.3.1 known issues`).

Documentation
~~~~~~~~~~~~~~~~~~~

* Add clarification about treatment of options when a spec-file is provided
  (#3039).
* Add docs for running PyInstaller with Python optimizations (#2905).

* Add notes about limitations of Cython support.
* Add information how to handle undetected ctypes libraries.
* Add notes about requirements and restrictions of SWIG support.
* Add note to clarify what `binary files` are.

* Add a Development Guide.
* Extend "How to Contribute".
* Add "Running the Test Suite".

* Remove badges from the Readme (#2853).

* Update outdated sections in man-pages and otehr enhancements to the
  man-page.


.. _v3.3.1 known issues:

Known Issues
~~~~~~~~~~~~~~~~~~

* All scripts frozen into the package, as well as all run-time hooks, share
  the same global variables. This issue exists since v3.2 but was discovered
  only lately, see :issue:`3037`. This may lead to leaking global variables
  from run-time hooks into the script and from one script to subsequent ones.
  It should have effects in rare cases only, though.

* Further see the :ref:`Known Issues for release 3.3 <v3.3 known issues>`.


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

.. _v3.3 known issues:

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


Older Versions
-----------------

.. toctree::
   :maxdepth: 1
   :caption: Older Versions

   CHANGES-3
   CHANGES-2
   CHANGES-1
             
.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
