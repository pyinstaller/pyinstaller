Changelog for PyInstaller 3.0 – 3.6
======================================================


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


3.4 (2018-09-09)
----------------

Features
~~~~~~~~

* Add support for Python 3.7 (:issue:`#2760`, :issue:`#3007`, :issue:`#3076`,
  :issue:`#3399`, :issue:`#3656`), implemented by Hartmut Goebel.
* Improved support for Qt5-based applications (:issue:`#3439`).
  By emulating much of the Qt deployment tools' behavior
  most PyQt5 variants are supported.
  However, Anaconda's PyQt5 packages are not supported
  because its ``QlibraryInfo`` implementation reports incorrect values.
  CI tests currently run on PyQt5 5.11.2. Many thanks to Bryan A. Jones for
  taking this struggle.
* ``--debug`` now allows more debugging to be activated more easily. This
  includes bootloader messages, Python's "verbose imports" and store collected
  Python files in the output directory instead of freezing. See ``pyinstaller
  –-help`` for details. (:issue:`#3546`, :issue:`#3585`, :issue:`#3587`)
* Hint users to install development package for missing `pyconfig.h`.
  (:issue:`#3348`)
* In ``setup.py`` specify Python versions this distribution is compatible with.
* Make ``base_library.zip`` reproducible: Set time-stamp of files. (:issue:`#2952`,
  :issue:`#2990`)
* New command-line option ``--bootloader-ignore-signals`` to make the
  bootloader forward all signals to the bundle application. (:issue:`#208`,
  :issue:`#3515`)
* (OS X) Python standard library module ``plistlib`` is now used for generating
  the ``Info.plist`` file. This allows passing complex and nested data in
  ``info_plist``. (:issue:`#3532`, :issue:`#3541`)


Bugfix
~~~~~~

* Add missing ``warnings`` module to ``base_library.zip``. (:issue:`#3397`,
  :issue:`#3400`)
* Fix and simplify search for libpython on Windows, msys2, cygwin.
  (:issue:`#3167`, :issue:`#3168`)
* Fix incompatibility with `pycryptodome` (a replacement for the apparently
  abandoned `pycrypto` library) when using encrypted PYZ-archives.
  (:issue:`#3537`)
* Fix race condition caused by the bootloader parent process terminating before
  the child is finished. This might happen e.g. when the child process itself
  plays with ``switch_root``. (:issue:`#2966`)
* Fix wrong security alert if a filename contains ``..``. (:issue:`#2641`,
  :issue:`#3491`)
* Only update resources of cached files when necessary to keep signature valid.
  (:issue:`#2526`)
* (OS X) Fix: App icon appears in the dock, even if ``LSUIElement=True``.
  (:issue:`#1917`, :issue:`#2075`, :issue:`#3566`)
* (Windows) Fix crash when trying to add resources to Windows executable using
  the ``--resource`` option. (:issue:`#2675`, :issue:`#3423`)
* (Windows) Only update resources when necessary to keep signature valid
  (:issue:`#3323`)
* (Windows) Use UTF-8 when reading XML manifest file. (:issue:`#3476`)
* (Windows) utils/win32: trap invalid ``--icon`` arguments and terminate with a
  message. (:issue:`#3126`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* Drop support for Python 3.3 (:issue:`#3288`), Thanks to Hugo and xoviat.
* ``--debug`` now expects an (optional) argument. Thus using ``… --debug
  script.py`` will break. Use ``… script.py --debug`` or ``… --debug=all
  script.py`` instead. Also ``--debug=all`` (which is the default if no
  argument is given) includes ``noarchive``, which will store all collected
  Python files in the output directory instead of freezing them. Use
  ``--debug=bootloader`` to get the former behavior. (:issue:`#3546`,
  :issue:`#3585`, :issue:`#3587`)
* (minor) Change naming of intermediate build files and the `warn` file. This
  only effects 3rd-party tools (if any exists) relying on the names of these
  files.
* (minor) The destination path for ``--add-data`` and ``--add-binary`` must no
  longer be empty, use ``.`` instead. (:issue:`#3066`)
* (minor) Use standard path, not dotted path, for C extensions (Python 3 only).


Hooks
~~~~~

* New hooks for bokeh visualization library (:issue:`#3607`),
  Champlain, Clutter (:issue:`#3443`) dynaconf (:issue:`#3641`), flex
  (:issue:`#3401`), FMPy (:issue:`#3589`), gi.repository.xlib
  (:issue:`#2634`, :issue:`#3396`) google-cloud-translate,
  google-api-core (:issue:`#3658`), jedi (:issue:`#3535`,
  :issue:`#3612`), nltk (:issue:`#3705`), pandas (:issue:`#2978`,
  :issue:`#2998`, :issue:`#2999`, :issue:`#3015`, :issue:`#3063`,
  :issue:`#3079`), phonenumbers (:issue:`#3381`, :issue:`#3558`),
  pinyin (:issue:`#2822`), PySide.phonon, PySide.QtSql
  (:issue:`#2859`), pytorch (:issue:`#3657`), scipy (:issue:`#2987`,
  :issue:`#3048`), uvloop (:issue:`#2898`), web3, eth_account,
  eth_keyfile (:issue:`#3365`, :issue:`#3373`).
* Updated hooks for Cryptodome 3.4.8, Django 2.1, gevent 1.3.
  Crypto (support for PyCryptodome) (:issue:`#3424`),
  Gst and GdkPixbuf (to work on msys2, :issue:`#3257`, :issue:`#3387`),
  sphinx 1.7.1, setuptools 39.0.
* Updated hooks for PyQt5 (:issue:`#1930`, :issue:`#1988`, :issue:`#2141`,
  :issue:`#2156`, :issue:`#2220`, :issue:`#2518`, :issue:`#2566`,
  :issue:`#2573`, :issue:`#2577`, :issue:`#2857`, :issue:`#2924`,
  :issue:`#2976`, :issue:`#3175`, :issue:`#3211`, :issue:`#3233`,
  :issue:`#3308`, :issue:`#3338`, :issue:`#3417`, :issue:`#3439`,
  :issue:`#3458`, :issue:`#3505`), among others:

  - All QML is now loaded by ``QtQml.QQmlEngine``.
  - Improve error reporting when determining the PyQt5 library location.
  - Improved method for finding ``qt.conf``.
  - Include OpenGL fallback DLLs for PyQt5. (:issue:`#3568`).
  - Place PyQt5 DLLs in the correct location (:issue:`#3583`).
* Fix hooks for cryptodome (:issue:`#3405`),
  PySide2 (style mismatch) (:issue:`#3374`, :issue:`#3578`)
* Fix missing SSL libraries on Windows with ``PyQt5.QtNetwork``. (:issue:`#3511`,
  :issue:`#3520`)
* Fix zmq on Windows Python 2.7. (:issue:`#2147`)
* (GNU/Linux) Fix hook usb: Resolve library name reported by usb.backend.
  (:issue:`#2633`, :issue:`#2831`, :issue:`#3269`)
* Clean up the USB hook logic.


Bootloader
~~~~~~~~~~

* Forward all signals to the child process if option
  ``pyi-bootloader-ignore-signals`` to be set in the archive. (:issue:`#208`,
  :issue:`#3515`)
* Use ``waitpid`` instead of ``wait`` to avoid the bootloder parent process gets
  signaled. (:issue:`#2966`)
* (OS X) Don't make the application a GUI app by default, even in
  ``--windowed`` mode. Not enforcing this programmatically in the bootloader
  allows to control behavior using ``Info.plist`` options - which can by set in
  PyInstaller itself or in the `.spec`-file. (:issue:`#1917`, :issue:`#2075`,
  :issue:`#3566`)
* (Windows) Show respectivly print utf-8 debug messages ungarbled.
  (:issue:`#3477`)
* Fix ``setenv()`` call when ``HAVE_UNSETENV`` is not defined. (:issue:`#3722`,
  :issue:`#3723`)


Module Loader
~~~~~~~~~~~~~

* Improved error message in case importing an extension module fails.
  (:issue:`#3017`)


Documentation
~~~~~~~~~~~~~

* Fix typos, smaller errors and formatting errors in documentation.
  (:issue:`#3442`, :issue:`#3521`, :issue:`#3561`, :issue:`#3638`)
* Make clear that ``--windowed`` is independent of ``--onedir``.
  (:issue:`#3383`)
* Mention imports using imports ``imp.find_module()`` are not detected.
* Reflect actual behavior regarding ``LD_LIBRARY_PATH``. (:issue:`#3236`)
* (OS X) Revise section on ``info_plist`` for ``plistlib`` functionality and
  use an example more aligned with real world usage. (:issue:`#3532`,
  :issue:`#3540`, :issue:`#3541`)
* (developers) Overhaul guidelines for commit and commit-messages.
  (:issue:`#3466`)
* (developers) Rework developer’s quick-start guide.


Project & Process
~~~~~~~~~~~~~~~~~

* Add a pip ``requirements.txt`` file.
* Let `pyup` update package requirements for “Test – Libraries” every month
  only.
* Use `towncrier` to manage the change log entries. (:issue:`#2756`,
  :issue:`#2837`, :issue:`#3698`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Add ``requirements_for_package()`` and ``collect_all()`` helper functions for
  hooks.
* Add a explanatory header to the warn-file, hopefully reducing the number of
  those posting the file to the issue tracker.
* Add module ``enum`` to base_library.zip, required for module ``re`` in
  Python 3.6 (and ``re`` is required by ``warnings``).
* Always write the `warn` file.
* Apply ``format_binaries_and_datas()`` (which converts hook-style tuples into
  ``TOC``-style tuples) to binaries and datas added through the hook api.
* Avoid printing a useless exceptions in the ``get_module_file_attribute()``
  helper function..
* Don't gather Python extensions in ``collect_dynamic_libc()``.
* Fix several ResourceWarnings and DeprecationWarnings (:issue:`#3677`)
* Hint users to install necessary development packages if, in
  ``format_binaries_and_datas()``, the file not found is ``pyconfig.h``.
  (:issue:`#1539`, :issue:`#3348`)
* Hook helper function ``is_module_satisfies()`` returns ``False`` for packages
  not found. (:issue:`#3428`, :issue:`#3481`)
* Read data for cache digest in chunks. (:issue:`#3281`)
* Select correct file extension for C-extension file-names like
  ``libzmq.cp36-win_amd64.pyd``.
* State type of import (conditional, delayed, etc.) in the *warn* file again.
* (modulegraph) Unbundle `altgraph` library, use from upstream.
  (:issue:`#3058`)
* (OS X) In ``--console`` mode set ``LSBackgroundOnly=True`` in``Info.plist`` to
  hide the app-icon in the dock. This can still be overruled by passing
  ``info_plist`` in the `.spec`-file. (:issue:`#1917`, :issue:`#3566`)
* (OS X) Use the python standard library ``plistlib`` for generating the
  ``Info.plist`` file. (:issue:`#3532`, :issue:`#3541`)
* (Windows) Completely remove `pywin32` dependency, which has erratic releases
  and the version on pypi may no longer have future releases. Require
  `pywin32-ctypes` instead, which is pure python. (:issue:`#3141`)
* (Windows) Encode manifest before updating resource. (:issue:`#3423`)
* (Windows) Make import compatible with python.net, which uses an incompatible
  signature for ``__import__``. (:issue:`#3574`)


Test-suite and Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add script and dockerfile for running tests in docker. (Contributed, not
  maintained) (:issue:`#3519`)
* Avoid log messages to be written (and captured) twice.
* Fix decorator ``skipif_no_compiler``.
* Fix the test for the "W" run-time Python option to verify module *warnings*
  can actually be imported. (:issue:`#3402`, :issue:`#3406`)
* Fix unicode errors when not capturing output by pytest.
* Run ``pyinstaller -h`` to verify it works.
* ``test_setuptools_nspkg`` no longer modifies source files.
* Appveyor:

  - Add documentation for Appveyor variables used to ``appveyor.yml``.
  - Significantly clean-up appveyor.yml (:issue:`#3107`)
  - Additional tests produce > 1 hour runs. Split each job into two
    jobs.
  - Appveyor tests run on 2 cores; therefore, run 2 jobs in parallel.
  - Reduce disk usage.
  - Split Python 2.7 tests into two jobs to avoid the 1 hour limit.
  - Update to use Windows Server 2016. (:issue:`#3563`)
* Travis

  - Use build-stages.
  - Clean-up travis.yml (:issue:`#3108`)
  - Fix Python installation on OS X. (:issue:`#3361`)
  - Start a X11 server for the "Test - Libraries" stage only.
  - Use target python interpreter to compile bootloader to check if the
    build tool can be used with that this Python version.


Bootloader build
~~~~~~~~~~~~~~~~

* Print invoking python version when compiling.
* Update `waf` build-tool to 2.0.9 and fix our ``wscript`` for `waf` 2.0.
* (GNU/Linux) When building with ``--debug`` turn of FORTIFY_SOURCE to ease
  debugging.


.. _v3.4 known issues:

Known Issues
~~~~~~~~~~~~~~~~~~

* Anaconda's PyQt5 packages are not supported
  because its ``QlibraryInfo`` implementation reports incorrect values.
* All scripts frozen into the package, as well as all run-time hooks, share
  the same global variables. This issue exists since v3.2 but was discovered
  only lately, see :issue:`3037`. This may lead to leaking global variables
  from run-time hooks into the script and from one script to subsequent ones.
  It should have effects in rare cases only, though.
* Data-files from wheels, unzipped eggs or not ad egg at all are not included
  automatically. This can be worked around using a hook-file, but may not
  suffice when using ``--onefile`` and something like `python-daemon`.

* The multipackage (MERGE) feature (:issue:`1527`) is currently broken.
* (OSX) Support for OpenDocument events (:issue:`1309`) is broken.
* (Windows) With Python 2.7 the frozen application may not run if the
  user-name (more specifically ``%TEMPDIR%``) includes some Unicode
  characters. This does not happen with all Unicode characters, but only some
  and seems to be a windows bug. As a work-around please upgrade to Python 3
  (:issue:`2754`, :issue:`2767`).
* (Windows) For Python >= 3.5 targeting *Windows < 10*, the developer needs to
  take special care to include the Visual C++ run-time .dlls. Please see the
  section :ref:`Platform-specific Notes <Platform-specific Notes - Windows>`
  in the manual. (:issue:`1566`)


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
- PyInstaller no longer extends :data:`sys.path` and bundled 3rd-party
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

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
