Changelog for PyInstaller
=========================

.. NOTE:

   You should *NOT* be adding new change log entries to this file, this
   file is managed by towncrier. You *may* edit previous change logs to
   fix problems like typo corrections or such.

   To add a new change log entry, please see
   https://pyinstaller.readthedocs.io/en/latest/development/changelog-entries.html

.. towncrier release notes start

4.3 (2021-04-16)
----------------

Features
~~~~~~~~

* Provide basic implementation for ``FrozenImporter.get_source()`` that
  allows reading source from ``.py`` files that are collected by hooks as
  data files. (:issue:`#5697`)
* Raise the maximum allowed size of ``CArchive`` (and consequently ``onefile``
  executables) from 2 GiB to 4 GiB. (:issue:`#3939`)
* The `unbuffered stdio` mode (the ``u`` option) now sets the
  ``Py_UnbufferedStdioFlag``
  flag to enable unbuffered stdio mode in Python library. (:issue:`#1441`)
* Windows: Set EXE checksums. Reduces false-positive detection from antiviral
  software. (:issue:`#5579`)
* Add new command-line options that map to collect functions from hookutils:
  ``-collect-submodules``, ``--collect-data``, ``--collect-binaries``,
  ``--collect-all``, and ``--copy-metadata``. (:issue:`#5391`)
* Add new hook utility :func:`~PyInstaller.utils.hooks.collect_entry_point` for
  collecting plugins defined through setuptools entry points. (:issue:`#5734`)


Bugfix
~~~~~~

* (macOS) Fix ``Bad CPU type in executable`` error in helper-spawned python
  processes when running under ``arm64``-only flavor of Python on Apple M1.
  (:issue:`#5640`)
* (OSX) Suppress missing library error messages for system libraries as
  those are never collected by PyInstaller and starting with Big Sur,
  they are hidden by the OS. (:issue:`#5107`)
* (Windows) Change default cache directory to ``LOCALAPPDATA``
  (from the original ``APPDATA``).
  This is to make sure that cached data
  doesn't get synced with the roaming profile.
  For this and future versions ``AppData\Roaming\pyinstaller``
  might be safely deleted. (:issue:`#5537`)
* (Windows) Fix ``onefile`` builds not having manifest embedded when icon is
  disabled via ``--icon NONE``. (:issue:`#5625`)
* (Windows) Fix the frozen program crashing immediately with
  ``Failed to execute script pyiboot01_bootstrap`` message when built in
  ``noconsole`` mode and with import logging enabled (either via
  ``--debug imports`` or ``--debug all`` command-line switch). (:issue:`#4213`)
* ``CArchiveReader`` now performs full back-to-front file search for
  ``MAGIC``, allowing ``pyi-archive_viewer`` to open binaries with extra
  appended data after embedded package (e.g., digital signature).
  (:issue:`#2372`)
* Fix ``MERGE()`` to properly set references to nested resources with their
  full shared-package-relative path instead of just basename. (:issue:`#5606`)
* Fix ``onefile`` builds failing to extract files when the full target
  path exceeds 260 characters. (:issue:`#5617`)
* Fix a crash in ``pyi-archive_viewer`` when quitting the application or
  moving up a level. (:issue:`#5554`)
* Fix extraction of nested files in ``onefile`` builds created in MSYS
  environments. (:issue:`#5569`)
* Fix installation issues stemming from unicode characters in
  file paths. (:issue:`#5678`)
* Fix the build-time error under python 3.7 and earlier when ``ctypes``
  is manually added to ``hiddenimports``. (:issue:`#3825`)
* Fix the return code if the frozen script fails due to unhandled exception.
  The return code 1 is used instead of -1, to keep the behavior consistent
  with that of the python interpreter. (:issue:`#5480`)
* Linux: Fix binary dependency scanner to support `changes to ldconfig
<https://sourceware.org/git/?p=glibc.git;a=commitdiff;h=dfb3f101c5ef23adf60d389058a2b33e23303d04>`_
  introduced in ``glibc`` 2.33. (:issue:`#5540`)
* Prevent ``MERGE`` (multipackage) from creating self-references for
  duplicated TOC entries. (:issue:`#5652`)
* PyInstaller-frozen onefile programs are now compatible with ``staticx``
  even if the bootloader is built as position-independent executable (PIE).
  (:issue:`#5330`)
* Remove dependence on a `private function
<https://github.com/matplotlib/matplotlib/commit/e1352c71f07aee7eab004b73dd9bda2a260ab31b>`_
  removed in ``matplotlib`` 3.4.0rc1. (:issue:`#5568`)
* Strip absolute paths from ``.pyc`` modules collected into
  ``base_library.zip``
  to enable reproducible builds that are invariant to Python install location.
  (:issue:`#5563`)
* (OSX) Fix issues with ``pycryptodomex`` on macOS. (:issue:`#5583`)
* Allow compiled modules to be collected into ``base_library.zip``.
  (:issue:`#5730`)
* Fix a build error triggered by scanning ``ctypes.CDLL('libc.so')`` on certain
  Linux C compiler combinations. (:issue:`#5734`)
* Improve performance and reduce stack usage of module scanning.
  (:issue:`#5698`)


Hooks
~~~~~

* Add support for Conda Forge's distribution of ``NumPy``. (:issue:`#5168`)
* Add support for package content listing via ``pkg_resources``. The
  implementation enables querying/listing resources in a frozen package
  (both PYZ-embedded and on-filesystem, in that order of precedence) via
  ``pkg_resources.resource_exists()``, ``resource_isdir()``, and
  ``resource_listdir()``. (:issue:`#5284`)
* Hooks: Import correct typelib for GtkosxApplication. (:issue:`#5475`)
* Prevent ``matplotlib`` hook from collecting current working directory when it
  fails to determine the path to matplotlib's data directory. (:issue:`#5629`)
* Update ``pandas`` hook for compatibility with version 1.2.0 and later.
  (:issue:`#5630`)
* Update hook for ``distutils.sysconfig`` to be compatible with
  pyenv-virtualenv. (:issue:`#5218`)
* Update hook for ``sqlalchemy`` to support version 1.4.0 and above.
  (:issue:`#5679`)
* Update hook for ``sysconfig`` to be compatible with pyenv-virtualenv.
  (:issue:`#5018`)


Bootloader
~~~~~~~~~~

* Implement full back-to-front file search for the embedded archive.
  (:issue:`#5511`)
* Perform file extraction from the embedded archive in a streaming manner
  in order to limit memory footprint when archive contains large files.
  (:issue:`#5551`)
* Set the ``__file__`` attribute in the ``__main__`` module (entry-point
  script) to the absolute file name inside the ``_MEIPASS``. (:issue:`#5649`)
* Enable cross compiling for FreeBSD from Linux. (:issue:`#5733`)


Documentation
~~~~~~~~~~~~~

* Doc: Add version spec file option for macOS Bundle. (:issue:`#5476`)
* Update the ``Run-time Information`` section to reflect the changes in
  behavior of ``__file__`` inside the ``__main__`` module. (:issue:`#5649`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Drop support for python 3.5; EOL since September 2020. (:issue:`#5439`)
* Collect python extension modules that correspond to built-ins into
  ``lib-dynload`` sub-directory instead of directly into bundle's root
  directory. This prevents them from shadowing shared libraries with the
  same basename that are located in a package and loaded via ``ctypes`` or
  ``cffi``, and also declutters the bundle's root directory. (:issue:`#5604`)


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
  apply any icon, thereby making the OS to show some default icon.
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
  contained in the executable and displayed for a shortcut. (:issue:`#870`,
  :issue:`#2995`)
* (Windows) Fix "toc is bad" error messages
  when passing a ``VSVersionInfo``
  as the ``version`` parameter to ``EXE()``
  in a ``.spec`` file. (:issue:`#5445`)
* (Windows) Fix exception when trying to read a manifest from an exe or dll.
  (:issue:`#5403`)
* (Windows) Fix the ``--runtime-tmpdir`` option by creating paths if they don't
  exist and expanding environment variables (e.g. ``%LOCALAPPDATA%``).
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
