Changelog for PyInstaller
=========================

.. NOTE:

   You should *NOT* be adding new change log entries to this file, this
   file is managed by towncrier. You *may* edit previous change logs to
   fix problems like typo corrections or such.

   To add a new change log entry, please see
   https://pyinstaller.readthedocs.io/en/latest/development/changelog-entries.html

.. towncrier release notes start

4.2 (2021-01-13)
----------------

Features
~~~~~~~~

* Add hooks utilities to find binary dependencies of Anaconda distributions.
  (:issue:`#5213`)
* (OSX) Automatically remove the signature from the collected copy of the
  ``Python`` shared library, using ``codesign --remove-signature``. This
  accommodates both ``onedir`` and ``onefile`` builds with recent python
  versions for macOS, where invalidated signature on PyInstaller-collected
  copy of the ``Python`` library prevents the latter from being loaded.
  (:issue:`#5451`)
* (Windows) PyInstaller's console or windowed icon is now added at freeze-time
  and
  no longer built into the bootloader. Also, using ``--icon=NONE`` allows to
  not
  apply any icon, thereby making the OS to show some defaultm icon.
  (:issue:`#4700`)
* (Windows) Enable ``longPathAware`` option in built application's manifest in
  order to support long file paths on Windows 10 v.1607 and later.
  (:issue:`#5424`)


Bugfix
~~~~~~

* Fix loading of plugin-type modules at run-time of the frozen application:
  If the plugin path is one character longer than sys._MEIPATH
  (e.g. "$PWD/p/plugin_1" and "$PWD/dist/main"),
  the plugin relative-imports a sub-module (of the plugin)
  and the frozen application contains a module of the same name,
  the frozen application module was imported. (:issue:`#4141`, :issue:`#4299`)
* Ensure that spec for frozen packages has ``submodule_search_locations`` set
  in order to fix compatibility  with ``importlib_resources`` 3.2.0 and later.
  (:issue:`#5396`)
* Fix: No rebuild if "noarchive" build-option changes. (:issue:`#5404`)
* (OSX) Fix the problem with ``Python`` shared library collected from
  recent python versions not being loaded due to invalidated signature.
  (:issue:`#5062`, :issue:`#5272`, :issue:`#5434`)
* (Windows) PyInstaller's default icon is no longer built into the bootloader,
  but
  added at freeze-time. Thus, when specifiying an icon, only that icon is
  contained in the executable and displaied for a shortcut. (:issue:`#870`,
  :issue:`#2995`)
* (Windows) Fix "toc is bad" error messages
  when passing a ``VSVersionInfo``
  as the ``version`` parameter to ``EXE()``
  in a ``.spec`` file. (:issue:`#5445`)
* (Windows) Fix exception when trying to read a manifest from an exe or dll.
  (:issue:`#5403`)
* (Windows) Fix the ``--runtime-tmpdir`` option by creating paths if they don't
  exist and expanding environment variables (e.g. %LOCALAPPDATA%).
  (:issue:`#3301`, :issue:`#4579`, :issue:`#4720`)


Hooks
~~~~~

* (GNU/Linux) Collect ``xcbglintegrations`` and ``egldeviceintegrations``
  plugins as part of ``Qt5Gui``. (:issue:`#5349`)
* (macOS) Fix: Unable to code sign apps built with GTK (:issue:`#5435`)
* (Windows) Add a hook for ``win32ctypes.core``. (:issue:`#5250`)
* Add hook for ``scipy.spatial.transform.rotation`` to fix compatibility with
  SciPy 1.6.0. (:issue:`#5456`)
* Add hook-gi.repository.GtkosxApplication to fix TypeError with Gtk macOS
  apps. (:issue:`#5385`)
* Add hooks utilities to find binary dependencies of Anaconda distributions.
  (:issue:`#5213`)
* Fix the ``Qt5`` library availability check in ``PyQt5`` and ``PySide2`` hooks
  to re-enable support for ``Qt5`` older than 5.8. (:issue:`#5425`)
* Implement ``exec_statement_rc()`` and ``exec_script_rc()`` as exit-code
  returning counterparts of ``exec_statement()`` and ``exec_script()``.
  Implement ``can_import_module()`` helper for hooks that need to query module
  availability. (:issue:`#5301`)
* Limit the impact of a failed sub-package import on the result of
  ``collect_submodules()`` to ensure that modules from all other sub-packages
  are collected. (:issue:`#5426`)
* Removed obsolete ``pygame`` hook. (:issue:`#5362`)
* Update ``keyring`` hook to collect metadata, which is required for backend
  discovery. (:issue:`#5245`)


Bootloader
~~~~~~~~~~

* (GNU/Linux) Reintroduce executable resolution via ``readlink()`` on
  ``/proc/self/exe`` and preserve the process name using ``prctl()`` with
  ``PR_GET_NAME`` and ``PR_SET_NAME``. (:issue:`#5232`)
* (Windows) Create temporary directories with user's SID instead of
  ``S-1-3-4``,
  to work around the lack of support for the latter in ``wine``.
  This enables ``onefile`` builds to run under ``wine`` again. (:issue:`#5216`)
* (Windows) Fix a bug in path-handling code with paths exceeding ``PATH_MAX``,
  which is caused by use of ``_snprintf`` instead of ``snprintf`` when
  building with MSC. Requires Visual Studio 2015 or later.
  Clean up the MSC codepath to address other compiler warnings.
  (:issue:`#5320`)
* (Windows) Fix building of bootloader's test suite under Windows with Visual
  Studio.
  This fixes build errors when ``cmocka`` is present in the build environment.
  (:issue:`#5318`)
* (Windows) Fix compiler warnings produced by MinGW 10.2 in order to allow
  building the bootloader without having to suppress the warnings.
  (:issue:`#5322`)
* (Windows) Fix ``windowed+debug`` bootloader variant not properly
  displaying the exception message and traceback information when the
  frozen script terminates due to uncaught exception. (:issue:`#5446`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* (Windows) Avoid using UPX with DLLs that have control flow guard (CFG)
  enabled. (:issue:`#5382`)
* Avoid using ``.pyo`` module file suffix (removed since PEP-488) in
  ``noarchive`` mode. (:issue:`#5383`)
* Improve support for ``PEP-420`` namespace packages. (:issue:`#5354`)
* Strip absolute paths from ``.pyc`` modules collected in the CArchive (PKG).
  This enables build reproducibility without having to match the location of
  the build environment. (:issue:`#5380`)


4.1 (2020-11-18)
----------------

Features
~~~~~~~~

* Add support for Python 3.9. (:issue:`#5289`)
* Add support for Python 3.8. (:issue:`#4311`)


Bugfix
~~~~~~

* Fix endless recursion if a package's ``__init__`` module is an extension
  module. (:issue:`#5157`)
* Remove duplicate logging messages (:issue:`#5277`)
* Fix sw_64 architecture support (:issue:`#5296`)
* (AIX) Include python-malloc labeled libraries in search for libpython.
  (:issue:`#4210`)


Hooks
~~~~~

* Add ``exclude_datas``, ``include_datas``, and ``filter_submodules`` to
  ``collect_all()``. These arguments map to the ``excludes`` and ``includes``
  arguments of ``collect_data_files``, and to the `filter` argument of
  ``collect_submodules``. (:issue:`#5113`)
* Add hook for difflib to not pull in doctests, which is only
  required when run as main programm.
* Add hook for distutils.util to not pull in lib2to3 unittests, which will be
  rearly used in frozen packages.
* Add hook for heapq to not pull in doctests, which is only
  required when run as main programm.
* Add hook for multiprocessing.util to not pull in python test-suite and thus
  e.g. tkinter.
* Add hook for numpy._pytesttester to not pull in pytest.
* Add hook for pickle to not pull in doctests and argpargs, which are only
  required when run as main programm.
* Add hook for PIL.ImageFilter to not pull
  numpy, which is an optional component.
* Add hook for setuptools to not pull in numpy, which is only imported if
  installed, not mean to be a dependency
* Add hook for zope.interface to not pull in pytest unittests, which will be
  rearly used in frozen packages.
* Add hook-gi.repository.HarfBuzz to fix Typelib error with Gtk apps.
  (:issue:`#5133`)
* Enable overriding Django settings path by `DJANGO_SETTINGS_MODULE`
  environment variable. (:issue:`#5267`)
* Fix `collect_system_data_files` to scan the given input path instead of its
  parent.
  File paths returned by `collect_all_system_data` are now relative to the
  input path. (:issue:`#5110`)
* Fix argument order in ``exec_script()`` and ``eval_script()``.
  (:issue:`#5300`)
* Gevent hook does not unnecessarily bundle HTML documentation, __pycache__
  folders, tests nor generated .c and .h files (:issue:`#4857`)
* gevent: Do not pull in test-suite (still to be refined)
* Modify hook for ``gevent`` to exclude test submodules. (:issue:`#5201`)
* Prevent .pyo files from being collected by collect_data_files when
  include_py_files is False. (:issue:`#5141`)
* Prevent output to ``stdout`` during module imports from ending up in the
  modules list collected by ``collect_submodules``. (:issue:`#5244`)
* Remove runtime hook and fix regular hook for matplotlib's data to support
  ``matplotlib>=3.3.0``, fix deprecation warning on version 3.1<= & <3.3,
  and behave normally for versions <3.1. (:issue:`#5006`)
* Remove support for deprecated PyQt4 and PySide (:issue:`#5118`,
  :issue:`#5126`)
* setuptools: Exclude outdated compat modules.
* Update ``sqlalchemy`` hook to support v1.3.19 and later,  by adding
  ``sqlalchemy.ext.baked`` as a hidden import (:issue:`#5128`)
* Update ``tkinter`` hook to collect Tcl modules directory (``tcl8``) in
  addition to Tcl/Tk data directories. (:issue:`#5175`)
* (GNU/Linux) {PyQt5,PySide2}.QtWebEngineWidgets: fix search for extra NSS
  libraries to prevent an error on systems where /lib64/nss/\*.so
  comes up empty. (:issue:`#5149`)
* (OSX) Avoid collecting data from system Tcl/Tk framework in ``tkinter`` hook
  as we do not collect their shared libraries, either.
  Affects only python versions that still use the system Tcl/Tk 8.5.
  (:issue:`#5217`)
* (OSX) Correctly locate the tcl/tk framework bundled with official
  python.org python builds from v.3.6.5 on. (:issue:`#5013`)
* (OSX) Fix the QTWEBENGINEPROCESS_PATH set in PyQt5.QtWebEngineWidgets rthook.
  (:issue:`#5183`)
* (OSX) PySide2.QtWebEngineWidgets: add QtQmlModels to included libraries.
  (:issue:`#5150`)
* (Windows) Remove the obsolete python2.4-era ``_handle_broken_tcl_tk``
  work-around for old virtual environments from the ``tkinter`` hook.
  (:issue:`#5222`)


Bootloader
~~~~~~~~~~

* Fix freeing memory allocted by Python using ``free()`` instead of
  ``PyMem_RawFree()``. (:issue:`#4441`)
* (GNU/Linux) Avoid segfault when temp path is missing. (:issue:`#5255`)
* (GNU/Linux) Replace a ``strncpy()`` call in ``pyi_path_dirname()`` with
  ``snprintf()`` to ensure that the resulting string is always null-terminated.
  (:issue:`#5212`)
* (OSX) Added capability for already-running apps to accept URL & drag'n drop
  events via Apple Event forwarding (:issue:`#5276`)
* (OSX) Bump ``MACOSX_DEPLOYMENT_TARGET`` from 10.7 to 10.13. (:issue:`#4627`,
  :issue:`#4886`)
* (OSX) Fix to reactivate running app on "reopen" (:issue:`#5295`)
* (Windows) Use ``_wfullpath()`` instead of ``_fullpath()`` in
  ``pyi_path_fullpath`` to allow non-ASCII characters in the path.
  (:issue:`#5189`)


Documentation
~~~~~~~~~~~~~

* Add zlib to build the requirements in the Building the Bootlooder section of
  the docs. (:issue:`#5130`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Add informative message what do to if RecurrsionError occurs.
  (:issue:`#4406`, :issue:`#5156`)
* Prevent a local directory with clashing name from shadowing a system library.
  (:issue:`#5182`)
* Use module loaders to get module content instea of an quirky way semming from
  early Python 2.x times. (:issue:`#5157`)
* (OSX) Exempt the ``Tcl``/``Tk`` dynamic libraries in the system framework
  from relative path overwrite. Fix missing ``Tcl``/``Tk`` dynlib on older
  python.org builds that still make use of the system framework.
  (:issue:`#5172`)


Test-suite and Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Replace ``skipif_xxx`` for platform-specific tests by markers.
  (:issue:`#1427`)
* Test/CI: Test failures are automatically retried once. (:issue:`#5214`)


Bootloader build
~~~~~~~~~~~~~~~~

* Fix AppImage builds that were broken since PyInstaller 3.6. (:issue:`#4693`)
* Update build system to use Python 3.
* OSX: Fixed the ineffectiveness of the ``--distpath`` argument for the
  ``BUNDLE`` step. (:issue:`#4892`)
* OSX: Improve codesigning and notarization robustness. (:issue:`#3550`,
  :issue:`#5112`)
* OSX: Use high resolution mode by default for GUI applications.
  (:issue:`#4337`)


4.0 (2020-08-08)
----------------

Features
~~~~~~~~

* Provide setuptools entrypoints to enable other packages to provide
  PyInstaller hooks specific to that package, along with tests for these
  hooks.

  Maintainers of Python packages requiring hooks are invited to use this new
  feature and provide up-to-date PyInstaller support along with their package.
  This is quite easy, see our `sample project`__ for more information
  (:issue:`#4232`, :issue:`#4301`, :issue:`#4582`).
  Many thanks to Bryan A. Jones for implementing the important parts.

  __ https://github.com/pyinstaller/hooksample

* A new package `pyinstaller-hooks-contrib`__ provides monthly updated hooks
  now. This package is installed automatically when installing PyInstaller,
  but can be updated independently.
  Many thanks to Legorooj for setting up the new package
  and moving the hooks there.

  __ https://github.com/pyinstaller/pyinstaller-hooks-contrib

* Added the ``excludes`` and ``includes`` arguments to the hook utility
  function ``collect_data_files``.
* Change the hook collection order so that the hook-priority is command line,
  then entry-point, then PyInstaller builtins. (:issue:`#4876`)


Bugfix
~~~~~~

* (AIX) Include python-malloc labeled libraries in search for libpython.
  (:issue:`#4738`)
* (win32) Fix Security Alerts caused by subtle implementation differences
  between posix anf windows in ``os.path.dirname()``. (:issue:`#4707`)
* (win32) Fix struct format strings for versioninfo. (:issue:`#4861`)
* (Windows) cv2: bundle the `opencv_videoio_ffmpeg*.dll`, if available.
  (:issue:`#4999`)
* (Windows) GLib: bundle the spawn helper executables for `g_spawn*` API.
  (:issue:`#5000`)
* (Windows) PySide2.QtNetwork: search for SSL DLLs in `PrefixPath` in addition
  to `BinariesPath`. (:issue:`#4998`)
* (Windows) When building with 32-bit python in onefile mode, set the
  ``requestedExecutionLevel`` manifest key every time and embed the manifest.
  (:issue:`#4992`)
* * (AIX) Fix uninitialized variable. (:issue:`#4728`, :issue:`#4734`)
* Allow building on a different drive than the source. (:issue:`#4820`)
* Consider Python<version> as possible library binary path. Fixes issue where
  python is not found if Python3 is installed via brew on OSX (:issue:`#4895`)
* Ensure shared dependencies from onefile packages can be opened in the
  bootloader.
* Ensuring repeatable builds of base_library.zip. (:issue:`#4654`)
* Fix ``FileNotFoundError`` showing up in ``utils/misc.py`` which occurs when a
  namespace was processed as an filename. (:issue:`#4034`)
* Fix multipackaging. The `MERGE` class will now have the correct relative
  paths
  between shared dependencies which can correctly be opened by the bootloader.
  (:issue:`#1527`, :issue:`#4303`)
* Fix regression when trying to avoid hard-coded paths in .spec files.
* Fix SIGTSTP signal handling to allow typing Ctrl-Z from terminal.
  (:issue:`#4244`)
* Update the base library to support encrypting Python bytecode (``--key``
  option) again. Many thanks to Matteo Bertini for finally fixing this.
  (:issue:`#2365`, :issue:`#3093`, :issue:`#3133`, :issue:`#3160`,
  :issue:`#3198`, :issue:`#3316`, :issue:`#3619`, :issue:`#4241`,
  :issue:`#4652`)
* When stripping the leading parts of paths in compiled code objects, the
  longest possible import path will now be stripped. (:issue:`#4922`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* Remove support for Python 2.7. The minimum required version is now Python
  3.5. The last version supporting Python 2.7 was PyInstaller 3.6.
  (:issue:`#4623`)
* Many hooks are now part of the new `pyinstaller-hooks-contrib`
  repository. See below for a detailed list.


Hooks
~~~~~

* Add hook for ``scipy.stats._stats`` (needed for scipy since 1.5.0).
  (:issue:`#4981`)
* Prevent hook-nltk from adding non-existing directories. (:issue:`#3900`)
* Fix ``importlib_resources`` hook for modern versions (after 1.1.0).
  (:issue:`#4889`)
* Fix hidden imports in `pkg_resources`__ and `packaging`__  (:issue:`#5044`)

  - Add yet more hidden imports to pkg_resources hook.
  - Mirror the pkg_resources hook for packaging which may or may not be
    duplicate of ``pkg_resources._vendor.packaging``.

  __ https://setuptools.readthedocs.io/en/latest/pkg_resources.html
  __ https://packaging.pypa.io/en/latest/

* Update pkg_resources hook for setuptools v45.0.0.
* Add QtQmlModels to included libraries for QtWebEngine on OS X
  (:issue:`#4631`).
* Fix detecting Qt5 libraries and dependencies from conda-forge builds
  (:issue:`#4636`).
* Add an AssertionError message so that users who get an error due
  to Hook conflicts can resolve it (:issue:`#4626`).

* These hooks have been moved to the new
  `pyinstaller-hooks-contrib`__ repository:
  BTrees, Crypto, Cryptodome, IPython, OpenGL, OpenGL_accelerate,
  Xlib, accessible_output2, adios, aliyunsdkcore, amazonproduct,
  appdirs, appy, astor, astroid, astropy, avro, bacon, boto, boto3,
  botocore, certifi, clr, countrycode, cryptography, cv2, cx_Oracle,
  cytoolz, dateparser, dclab, distorm3, dns, docutils, docx, dynaconf,
  enchant, enzyme, eth_abi, eth_account, eth_hash, eth_keyfile,
  eth_utils, faker, flex, fmpy, gadfly, gooey, google.*, gst, gtk,
  h5py, httplib, httplib2, imageio, imageio_ffmpeg, jedi, jinja2,
  jira, jsonpath_rw_ext, jsonschema, jupyterlab, kinterbasdb,
  langcodes, lensfunpy, libaudioverse, llvmlite, logilab, lxml, lz4,
  magic, mako, markdown, migrate, mpl_toolkits, mssql, mysql, nacl,
  names, nanite, nbconvert, nbdime, nbformat, ncclient, netCDF4, nltk,
  nnpy, notebook, numba, openpyxl, osgeo, passlib, paste, patsy,
  pendulum, phonenumbers, pint, pinyin, psychopy, psycopg2, pubsub,
  pyarrow, pycountry, pycparser, pyexcel, pyexcelerate, pylint,
  pymssql, pyodbc, pyopencl, pyproj, pysnmp, pytest, pythoncom,
  pyttsx, pywintypes, pywt, radicale, raven, rawpy, rdflib, redmine,
  regex, reportlab, reportlab, resampy, selenium, shapely, skimage,
  sklearn, sound_lib, sounddevice, soundfile, speech_recognition,
  storm, tables, tcod, tensorflow, tensorflow_corethon,
  text_unidecode, textdistance, torch, ttkthemes, ttkwidgets, u1db,
  umap, unidecode, uniseg, usb, uvloop, vtkpython, wavefile,
  weasyprint, web3, webrtcvad, webview, win32com, wx, xml.dom,
  xml.sax, xsge_gui, zeep, zmq.

  __ https://github.com/pyinstaller/pyinstaller-hooks-contrib

* These hooks have been added while now moved to the new
  `pyinstaller-hooks-contrib` repository: astor (:issue:`4400`,
  :issue:`#4704`), argon2 (:issue:`#4625`) bcrypt. (:issue:`#4735`),
  (Bluetooth Low Energy platform Agnostic Klient for Python) (:issue:`#4649`)
  jaraco.text (:issue:`#4576`, :issue:`#4632`), LightGBM. (:issue:`#4634`),
  xmldiff (:issue:`#4680`), puremagic (identify a file based off it's magic
  numbers) (:issue:`#4709`) webassets (:issue:`#4760`), tensorflow_core (to
  support tensorflow module forwarding logic (:issue:`4400`, :issue:`#4704`)

* These changes have been applied to hooks now moved to the new
  `pyinstaller-hooks-contrib` repository

  - Update Bokeh hook for v2.0.0. (:issue:`#4742`, :issue:`#4746`)
  - Fix shapely hook on Windows for non-conda shapely installations.
    (:issue:`#2834`, :issue:`#4749`)


Bootloader
~~~~~~~~~~

* Rework bootloader from using strcpy/strncpy with "is this string
  terminated"-check to use snprintf(); check succes at more places. (This
  started from fixing GCC warnings for strncpy and strncat.)
* Fix: When copying files, too much data was copied in most cases. This
  corrupted the file and inhibited using shared dependencies. (:issue:`#4303`)
* In debug and windowed mode, show the traceback in dialogs to help debug
  pyiboot01_bootstrap errors. (:issue:`#4213`, :issue:`#4592`)
* Started a small test-suite for bootloader basic functions. (:issue:`#4585`)


Documentation
~~~~~~~~~~~~~

* Add platform-specific usage notes and bootloader build notes for AIX.
  (:issue:`#4731`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Provide setuptools entrypoints to enable other packages to provide
  PyInstaller hooks specific to that package, along with tests for these hooks.
  See https://github.com/pyinstaller/hooksample for more information.
  (:issue:`#4232`, :issue:`#4582`)


Bootloader build
~~~~~~~~~~~~~~~~

* (AIX) The argument -X32 or -X64 is not recognized by the AIX loader - so this
  code needs to be removed. (:issue:`#4730`, :issue:`#4731`)
* (OSX) Allow end users to override MACOSX_DEPLOYMENT_TARGET and
  mmacosx-version-min
  via environment variables and set 10.7 as the fallback value for both.
  (:issue:`#4677`)
* Do not print info about ``--noconfirm`` when option is already being used.
  (:issue:`#4727`)
* Update :command:`waf` to version 2.0.20 (:issue:`#4839`)



3.6 (2020-01-09)
--------------------------

**Important:** This is the last release of PyInstaller supporting Python 2.7.
Python 2 is end-of-life, many packages are about to `drop support for Python
2.7 <https://python3statement.org/>`_ - or already did it.

Security
~~~~~~~~

* [SECURITY] (Win32) Fix CVE-2019-16784: Local Privilege Escalation caused by
  insecure directory permissions of sys._MEIPATH. This security fix effects all
  Windows software frozen by PyInstaller in "onefile" mode.
  While PyInstaller itself was not vulnerable, all Windows software frozen
  by PyInstaller in "onefile" mode is vulnerable.

  If you are using PyInstaller to freeze Windows software using "onefile"
  mode, you should upgrade PyInstaller and rebuild your software.


Features
~~~~~~~~

* (Windows): Applications built in windowed mode have their debug messages
  sent to any attached debugger or DebugView instead of message boxes.
  (:issue:`#4288`)
* Better error message when file exists at path we want to be dir.
  (:issue:`#4591`)


Bugfix
~~~~~~

* (Windows) Allow usage of `VSVersionInfo` as version argument to EXE again.
  (:issue:`#4381`, :issue:`#4539`)
* (Windows) Fix MSYS2 dll's are not found by modulegraph. (:issue:`#4125`,
  :issue:`#4417`)
* (Windows) The temporary copy of bootloader used add resources, icons, etc.
  is not created in --workpath instead of in  %TEMP%. This fixes issues on
  systems where the anti-virus cleans %TEMP% immediately. (:issue:`#3869`)
* Do not fail the build when ``ldconfig`` is missing/inoperable.
  (:issue:`#4261`)
* Fixed loading of IPython extensions. (:issue:`#4271`)
* Fixed pre-find-module-path hook for `distutils` to be compatible with
  `virtualenv >= 16.3`. (:issue:`#4064`, :issue:`#4372`)
* Improve error reporting when the Python library can't be found.
  (:issue:`#4162`)


Hooks
~~~~~

* Add hook for
  avro (serialization and RPC framework) (:issue:`#4388`),
  `django-babel <https://github.com/python-babel/django-babel>`_ (:issue:`#4516`),
  `enzyme <https://pypi.org/project/enzyme/>`_ (:issue:`#4338`),
  google.api (resp. google.api.core) (:issue:`#3251`),
  google.cloud.bigquery (:issue:`#4083`, :issue:`#4084`),
  google.cloud.pubsub (:issue:`#4446`),
  google.cloud.speech (:issue:`#3888`),
  nnpy (:issue:`#4483`),
  passlib (:issue:`#4520`),
  `pyarrow <https://pypi.org/project/pyarrow/>`_ (:issue:`#3720`, :issue:`#4517`),
  pyexcel and its plugins io, ods, ods3, odsr, xls, xlsx, xlsxw (:issue:`#4305`),
  pysnmp (:issue:`#4287`),
  scrapy (:issue:`#4514`),
  skimage.io (:issue:`#3934`),
  sklearn.mixture (:issue:`#4612`),
  sounddevice on macOS and Windows (:issue:`#4498`),
  text-unidecode (:issue:`#4327`, :issue:`#4530`),
  the google-cloud-kms client library (:issue:`#4408`),
  ttkwidgets (:issue:`#4484`), and
  webrtcvad (:issue:`#4490`).
* Correct the location of Qt translation files. (:issue:`#4429`)
* Exclude imports for pkg_resources to fix bundling issue. (:issue:`#4263`,
  :issue:`#4360`)
* Fix hook for pywebview to collect all required libraries and data-files.
  (:issue:`#4312`)
* Fix hook numpy and hook scipy to account for differences in location of extra
  dlls on Windows. (:issue:`#4593`)
* Fix pysoundfile hook to bundle files correctly on both OSX and Windows.
  (:issue:`#4325`)
* Fixed hook for `pint <https://github.com/hgrecco/pint>`_
  to also copy metadata as required to retrieve the version at runtime.
  (:issue:`#4280`)
* Fixed PySide2.QtNetwork hook by mirroring PyQt5 approach. (:issue:`#4467`,
  :issue:`#4468`)
* Hook for pywebview now collects data files and dynamic libraries only for the
  correct OS (Windows).
  Hook for pywebview now bundles only the required 'lib' subdirectory.
  (:issue:`#4375`)
* Update hooks related to PySide2.QtWebEngineWidgets, ensure the relevant
  supporting files required for a QtWebEngineView are copied into the
  distribution. (:issue:`#4377`)
* Update PyQt5 loader to support PyQt >=5.12.3. (:issue:`#4293`,
  :issue:`#4332`)
* Update PyQt5 to package 64-bit SSL support DLLs. (:issue:`#4321`)
* Update PyQt5 to place OpenGL DLLs correctly for PyQt >= 5.12.3.
  (:issue:`#4322`)
* (GNU/Linux) Make hook for GdkPixbuf compatible with Ubuntu and Debian
  (:issue:`#4486`).


Bootloader
~~~~~~~~~~

* (OSX): Added support for appending URL to program arguments when applications
  is launched from custom protocol handler. (:issue:`#4397`, :issue:`#4399`)
* (POSIX) For one-file binaries, if the program is started via a symlink, the
  second process now keeps the basename of the symlink. (:issue:`#3823`,
  :issue:`#3829`)
* (Windows) If bundled with the application, proactivley load ``ucrtbase.dll``
  before loading the Python library. This works around unresolved symbol errors
  when loading ``python35.dll`` (or later) on legacy Windows (7, 8, 8.1)
  systems
  with Universal CRT update is not installed. (:issue:`#1566`, :issue:`#2170`,
  :issue:`#4230`)
* Add our own implementation for ``strndup`` and ``strnlen`` to be used on
  platforms one of these is missing.


PyInstaller Core
~~~~~~~~~~~~~~~~

* Now uses hash based `.pyc` files as specified in :pep:`552` in
  `base_library.zip` when using Python 3.7 (:issue:`#4096`)


Bootloader build
~~~~~~~~~~~~~~~~

* (MinGW-w64) Fix .rc.o file not found error. (:issue:`#4501`, :issue:`#4586`)
* Add a check whether ``strndup`` and ``strnlen`` are available.
* Added OpenBSD support. (:issue:`#4545`)
* Fix build on Solaris 10.
* Fix checking for compiler flags in `configure` phase. The check for compiler
  flags actually did never work. (:issue:`#4278`)
* Update url for public key in update-waf script. (:issue:`#4584`)
* Update waf to version 2.0.19.


3.5 (2019-07-09)
----------------

Features
~~~~~~~~

* (Windows) Force ``--windowed`` option if first script is a ``.pyw`` file.
  This might still be overwritten in the spec-file. (:issue:`#4001`)
* Add support for relative paths for icon-files, resource-files and
  version-resource-files. (:issue:`#3333`, :issue:`#3444`)
* Add support for the RedHat Software Collections (SCL) Python 3.x.
  (:issue:`#3536`, :issue:`#3881`)
* Install platform-specific dependencies only on that platform.
  (:issue:`#4166`, :issue:`#4173`)
* New command-line option ``--upx-exclude``, which allows the user to prevent
  binaries from being compressed with UPX. (:issue:`#3821`)


Bugfix
~~~~~~

* (conda) Fix detection of conda/anaconda platform.
* (GNU/Linux) Fix Anaconda Python library search. (:issue:`#3885`,
  :issue:`#4015`)
* (Windows) Fix UAC in one-file mode by embedding the manifest.
  (:issue:`#1729`, :issue:`#3746`)
* (Windows\\Py3.7) Now able to locate pylib when VERSION.dll is listed in
  python.exe PE Header rather than pythonXY.dll (:issue:`#3942`,
  :issue:`#3956`)
* Avoid errors if PyQt5 or PySide2 is referenced by the modulegraph but isn't
  importable. (:issue:`#3997`)
* Correctly parse the ``--debug=import``, ``--debug=bootloader``, and
  ``--debug=noarchive`` command-line options. (:issue:`#3808`)
* Don't treat PyQt5 and PySide2 files as resources in an OS X windowed build.
  Doing so causes the resulting frozen app to fail under Qt 5.12.
  (:issue:`#4237`)
* Explicitly specify an encoding of UTF-8 when opening *all* text files.
  (:issue:`#3605`)
* Fix appending the content of ``datas`` in a `spec` files to ``binaries``
  instead of the internal ``datas``. (:issue:`#2326`, :issue:`#3694`)
* Fix crash when changing from ``--onefile`` to ``--onedir`` on consecutive
  runs. (:issue:`#3662`)
* Fix discovery of Qt paths on Anaconda. (:issue:`#3740`)
* Fix encoding error raised when reading a XML manifest file which includes
  non-ASCII characters. This error inhibited building an executable which
  has non-ASCII characters in the filename. (:issue:`#3478`)
* Fix inputs to ``QCoreApplication`` constructor in ``Qt5LibraryInfo``. Now the
  core application's initialization and finalization in addition to system-wide
  and application-wide settings is safer. (:issue:`#4121`)
* Fix installation with pip 19.0. (:issue:`#4003`)
* Fixes PE-file corruption during version update. (:issue:`#3142`,
  :issue:`#3572`)
* In the fake ´site` module set `USER_BASE` to empty string instead of None
  as Jupyter Notebook requires it to be a 'str'. (:issue:`#3945`)
* Query PyQt5 to determine if SSL is supported, only adding SSL DLLs if so. In
  addition, search the path for SSL DLLs, instead of looking in Qt's
  ``BinariesPath``. (:issue:`#4048`)
* Require ``pywin32-ctypes`` version 0.2.0, the minimum version which supports
  Python 3.7. (:issue:`#3763`)
* Use pkgutil instead of filesystem operations for interacting with the
  modules. (:issue:`#4181`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* PyInstaller is no longer tested against Python 3.4, which is end-of-live.
* Functions ``compat.architecture()``, ``compat.system()`` and
  ``compat.machine()`` have been replace by variables of the same name. This
  avoids evaluating the save several times.
* Require an option for the ``--debug`` argument, rather than assuming a
  default of ``all``. (:issue:`#3737`)


Hooks
~~~~~

* Added hooks for
  `aliyunsdkcore <https://pypi.org/project/aliyun-python-sdk-core/>`_ (:issue:`#4228`),
  astropy (:issue:`#4274`),
  `BTrees <https://pypi.org/project/BTrees/>`_ (:issue:`#4239`),
  dateparser.utils.strptime (:issue:`#3790`),
  `faker <https://faker.readthedocs.io>`_ (:issue:`#3989`, :issue:`#4133`),
  gooey (:issue:`#3773`),
  GtkSourceView (:issue:`#3893`),
  imageio_ffmpeg (:issue:`#4051`),
  importlib_metadata and importlib_resources (:issue:`#4095`),
  jsonpath_rw_ext (:issue:`#3841`),
  jupyterlab (:issue:`#3951`),
  lz4 (:issue:`#3710`),
  `magic <https://pypi.org/project/python-magic-bin>`_ (:issue:`#4267`),
  nanite (:issue:`#3860`),
  nbconvert (:issue:`#3947`),
  nbdime (:issue:`#3949`),
  nbformat (:issue:`#3946`),
  notebook (:issue:`#3950`),
  pendulum (:issue:`#3906`),
  pysoundfile (:issue:`#3844`),
  python-docx (:issue:`#2574`, :issue:`#3848`),
  python-wavefile (:issue:`#3785`),
  pytzdata (:issue:`#3906`),
  `PyWavelets pywt <https://github.com/PyWavelets/pywt>`_ (:issue:`#4120`),
  pywebview (:issue:`#3771`),
  radicale (:issue:`#4109`),
  rdflib (:issue:`#3708`),
  resampy (:issue:`#3702`),
  `sqlalchemy-migrate <https://github.com/openstack/sqlalchemy-migrate>`_ (:issue:`#4250`),
  `textdistance <https://pypi.org/project/textdistance/>`_ (:issue:`#4239`),
  tcod (:issue:`#3622`),
  ttkthemes (:issue:`#4105`), and
  `umap-learn <https://umap-learn.readthedocs.io/en/latest/>`_ (:issue:`#4165`).
  
* Add runtime hook for certifi. (:issue:`#3952`)
* Updated hook for 'notebook' to look in all Jupyter paths reported by
  jupyter_core. (:issue:`#4270`)
* Fixed hook for 'notebook' to only include directories that actually exist.
  (:issue:`#4270`)
  
* Fixed pre-safe-import-module hook for `setuptools.extern.six`. (:issue:`#3806`)
* Fixed QtWebEngine hook on OS X. (:issue:`#3661`)
* Fixed the QtWebEngine hook on distributions which don't have a NSS subdir
  (such as Archlinux) (:issue:`#3758`)
* Include dynamically-imported backends in the ``eth_hash`` package.
  (:issue:`#3681`)
* Install platform-specific dependencies only on that platform.
  (:issue:`#4168`)
* Skip packaging PyQt5 QML files if the QML directory doesn't exist.
  (:issue:`#3864`)
* Support ECC in PyCryptodome. (:issue:`#4212`, :issue:`#4229`)
* Updated PySide2 hooks to follow PyQt5 approach. (:issue:`#3655`,
  :issue:`#3689`, :issue:`#3724`, :issue:`#4040`, :issue:`#4103`,
  :issue:`#4136`, :issue:`#4175`, :issue:`#4177`, :issue:`#4198`,
  :issue:`#4206`)
* Updated the jsonschema hook for v3.0+. (:issue:`#4100`)
* Updated the Sphinx hook to correctly package Sphinx 1.8.


Bootloader
~~~~~~~~~~

* Update bundled zlib library to 1.2.11 address vulnerabilities.
  (:issue:`#3742`)


Documentation
~~~~~~~~~~~~~

* Update the text produced by ``--help`` to state that the ``--debug`` argument
  requires an option. Correctly format this argument in the Sphinx build
  process. (:issue:`#3737`)


Project & Process
~~~~~~~~~~~~~~~~~

* Remove the PEP-518 "build-system" table from ``pyproject.toml`` to fix
  installation with pip 19.0.


PyInstaller Core
~~~~~~~~~~~~~~~~

* Add support for folders in `COLLECT` and `BUNDLE`. (:issue:`#3653`)
* Completely remove `pywin32` dependency, which has erratic releases and
  the version on pypi may no longer have future releases.
  Require `pywin32-ctypes` instead which is pure python. (:issue:`#3728`,
  :issue:`#3729`)
* modulegraph: Align with upstream version 0.17.
* Now prints a more descriptive error when running a tool fails (instead of
  dumping a trace-back). (:issue:`#3772`)
* Suppress warnings about missing UCRT dependencies on Win 10. (:issue:`#1566`,
  :issue:`#3736`)


Test-suite and Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Fix Appveyor failures of ``test_stderr_encoding()`` and
  ``test_stdout_encoding()`` on Windows Python 3.7 x64. (:issue:`#4144`)
* November update of packages used in testing. Prevent pyup from touching
  ``test/requirements-tools.txt``. (:issue:`#3845`)
* Rewrite code to avoid a ``RemovedInPytest4Warning: Applying marks directly to
  parameters is deprecated, please use pytest.param(..., marks=...) instead.``
* Run Travis tests under Xenial; remove the deprecated ``sudo: false`` tag.
  (:issue:`#4140`)
* Update the Markdown test to comply with `Markdown 3.0 changes
  <https://python-markdown.github.io/change_log/release-3.0/#positional-arguments-deprecated>`_
  by using correct syntax for `extensions
  <https://python-markdown.github.io/reference/#extensions>`_.


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
