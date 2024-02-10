Changelog for PyInstaller
=========================

.. NOTE:

   You should *NOT* be adding new change log entries to this file, this
   file is managed by towncrier. You *may* edit previous change logs to
   fix problems like typo corrections or such.

   To add a new change log entry, please see
   https://pyinstaller.readthedocs.io/en/latest/development/changelog-entries.html

.. Preview unreleased news fragments.
.. towncrier-draft-entries:: The Next Release

.. towncrier release notes start

6.4.0 (2024-02-10)
------------------

Features
~~~~~~~~

* (Linux) Collect ``.hmac`` files accompanying shared libraries, if such files
  are available. This allows frozen application to run on FIPS-enabled Red Hat
  Enterprise systems, where HMAC is required by self-check implemented by the
  OpenSSL crypto library. Furthermore, ensure that shared libraries with
  accompanying ``.hmac`` files are exempted from any additional processing (for
  example, when building with :option:`--strip` option) to avoid invalidating
  the HMAC. (:issue:`8273`)
* (Windows) Make bootloader codepaths involved in creation of temporary
  directories for ``onefile`` builds AppContainer-aware. If the process runs
  inside an AppContainer, the temporary directory's DACL needs to explicitly
  include the AppContainerSID, otherwise the directory becomes inaccessible to
  the process. (:issue:`8291`)
* (Windows) Make Windows implementation of PyInstaller's
  ``_pyi_rth_utils.tempdir.secure_mkdir`` (used by ``matplotlib`` and
  ``win32com`` run-time hooks to create temporary directories)
  AppContainer-aware. If the process runs inside an AppContainer, the temporary
  directory's DACL needs to explicitly include the AppContainerSID, otherwise
  the directory becomes inaccessible to the process. (:issue:`8290`)
* Implement strict Qt dependency validation for collection of Qt plugins and QML
  components/plugins. We now perform preliminary binary dependency analysis of
  the plugins, and automatically exclude plugins that have at least one missing
  Qt dependency. This prevents collection of plugins that cannot be used anyway
  because of a missing Qt shared library (that is, for example, omitted from a
  PyPI wheel). Furthermore, we disallow Qt dependencies of a plugin to be
  resolved outside of the primary location of Qt shared libraries, in order to
  prevent missing dependencies from pulling in Qt libraries from alternative
  locations that happen to be in the search path (for example, when using
  ``PyQt5`` PyPI wheels while also having a system-installed Qt5 on Linux, a
  Homebrew-installed Qt5 on macOS, or a custom Windows Qt5 build that happens to
  be in ``PATH``). (:issue:`8226`)


Bugfix
~~~~~~

* (Linux) Prevent collection of ``libcuda.so.1``, which is part of NVIDIA
  driver and must match the rest of the driver's components. Collecting
  a copy might lead to issues when build and target system use different
  versions of NVIDIA driver. (:issue:`8278`)
* (macOS) When validating the macOS SDK version of collected binaries,
  handle errors raised by ``osxutils.get_macos_sdk_version``; log a
  warning about failed version query, and add the offending binary to
  the list of potentially problematic binaries to warn the user about.
  (:issue:`8220`)
* Fix ``pkgutil.iter_modules`` override to gracefully handle cases when
  the given path corresponds to a module instead of a package. (:issue:`8191`)
* Prevent Qt and QML plugins with missing Qt dependencies in the
  ``PySide2``, ``PyQt5``, ``PySide6``, and ``PyQt6`` PyPI wheels from
  pulling in Qt shared libraries from alternative locations (for example,
  system-installed Qt on Linux, Homebrew-installed Qt on macOS, or
  a custom Windows Qt build that happens to be in ``PATH``), and resulting
  in a frozen application that contains an incompatible mix of Qt libraries.
  (:issue:`8087`)
* Switch the hashing function in PyInstaller's binary cache from MD5 to
  SHA1, as the former cannot be used on FIPS-enabled Red Hat Enterprise
  Linux systems. (:issue:`8288`)
* When trying to run ``pyinstaller`` (or equivalent ``python -m PyInstaller``)
  against non-existing script file(s), exit immediately - without trying
  to write the .spec file and building it. This prevents us from overwriting
  an existing (and customized) .spec file if user makes a typo in the .spec
  file's suffix when trying to build it, for example, ``pyinstaller
  program.cpes``. (:issue:`8279`)


Hooks
~~~~~

* (macOS) Have ``PySide6`` and ``PyQt6`` run-time hooks prepend
  ``sys._MEIPASS`` to ``DYLD_LIBRARY_PATH`` in POSIX builds, in order
  to ensure that ``QtNetwork`` discovers the bundled copy of the OpenSSL
  shared library. (:issue:`8226`)
* Extend the OpenSSL shared library collection in the ``QtNetwork`` hook
  helper for ``PySide2``, ``PyQt5``, ``PySide6``, and ``PyQt6`` to
  cover all applicable versions of OpenSSL (1.0.2, 1.1.x, 3.x). In
  addition to Windows, the OpenSSL shared library is now also collected
  on Linux and macOS. (:issue:`8226`)


Bootloader
~~~~~~~~~~

* (Windows) Update the bundled zlib sources to v1.3.1. (:issue:`8292`)


Documentation
~~~~~~~~~~~~~

* Add a new documentation chapter, called :ref:`common issues`, to cover
  topics such as launching external programs from frozen applications,
  multi-processing via :mod:`multiprocessing` (specifically, the requirement
  to call :func:`multiprocessing.freeze_support`), use of symbolic links in
  POSIX builds in PyInstaller >= 6.0 and its implications for distribution
  (e.g., when copying frozen application, or creating ``zip`` archives),
  :data:`sys.stdout` and :data:`sys.stderr` being :data:`None` in Windows
  no-console builds. (:issue:`8214`)
* Cleanup docstrings to remove mention of ``exec_command_stdout``.
  (:issue:`8173`)
* Update the :ref:`macOS app bundles` section to reflect the layout of
  macOS app bundles as produced by PyInstaller 6.0 and later. Add a note
  to discourage use of onefile .app bundles. (:issue:`8214`)
* Update the introduction part of the :ref:`understanding pyinstaller hooks`
  section. (:issue:`8214`)


6.3.0 (2023-12-10)
------------------

Bugfix
~~~~~~

* (Linux) Optimize the automatic binary-vs-data classification by avoiding
  ``objdump`` based check on files that do not have ELF signature. This
  mitigates noticeably longer analysis times for projects with large number of
  (data) files. (:issue:`8148`)
* (Windows) Add Windows error code 110 (``ERROR_OPEN_FAILED``) to the list of
  error codes eligible for the retry mechanism that attempts to mitigate build
  failures due to anti-virus program interference. (:issue:`8138`)
* (Windows) Fix issue with non-functional :func:`time.sleep()` when building
  program with Python <= 3.8.6 or Python 3.9.0. (:issue:`8104`)
* (Windows) Fix issue with splash screen in ``onefile`` mode failing to extract
  ``VCRUNTIME140.dll`` from the archive due to character-case mismatch. We now
  perform case-insensitive comparison between the name listed in splash
  dependency list and the names in archive TOC. (:issue:`8103`)
* Fix PEP 597 EncodingWarnings when :envvar:`PYTHONWARNDEFAULTENCODING` is set
  to true. (:issue:`8117`)
* Fix pre-safe-import hooks for ``six.moves``, ``urllib3.packages.six.moves``,
  and ``setuptools.extern.six.moves`` to gracefully handle cases when the
  corresponding ``six`` package is unavailable, as the hook may end up being
  executed even in that case. (:issue:`8145`)
* Fix symbolic link tracking in ``MERGE`` processing, so that distinct symbolic
  links with same relative target (e.g. ``Current -> A`` symbolic links in Qt
  .framework bundles collected on macOS) are properly processed, and kept in the
  original TOC upon their first occurrence. (:issue:`8124`)


Hooks
~~~~~

* Add hook for ``gi.repository.DBus``. (:issue:`8149`)
* Add hooks for ``gi.repository.AppIndicator3`` and
  ``gi.repository.AyatanaAppIndicator3``. (:issue:`8149`)


Bootloader
~~~~~~~~~~

* When setting up embedded Python interpreter configuration, set
  ``PyConfig.install_signal_handlers=1`` to install signal handlers.
  This matches the behavior of PyInstaller 5.x bootloaders, where interpreter
  was initialized via ``Py_Initialize()``, which in turn calls
  ``Py_InitializeEx(1)``, i.e., with ``install_sigs=1``. (:issue:`8105`)


6.2.0 (2023-11-11)
------------------

Features
~~~~~~~~

* (macOS) At the end of analysis, verify the macOS SDK version reported
  by binaries to be collected, and warn when the version is either invalid
  (0.0.0) or too low (< 10.9.0). Such binaries will likely cause issues
  with code-signing and hardened runtime. (:issue:`8043`)
* If the ``argcomplete`` Python module is installed, PyInstaller will use it
  enable tab completion for its CLI tools. PyInstaller CLIs can still be used
  without this optional dependency. To install ``argcomplete`` with
  PyInstaller, you can put ``pyinstaller[completion]`` in your dependencies.
  See also `the argcomplete documentation
  <https://kislyuk.github.io/argcomplete/>`_. (:issue:`8008`)


Bugfix
~~~~~~

* (macOS) Fix the bug in binary processing and caching that would update
  the binary cache index before performing macOS-specific processing
  (architecture validation, path rewriting). If, for example, architecture
  validation failed during a build, subsequent build attempts with
  enabled binary cache (i.e., without the :option:`--clean` option) would
  pick up the partially-processed binary file from the cache, bypassing the
  architecture validation. NOTE: the existing binary caches need to be
  purged manually (using :option:`--clean` option once) for the fix to take
  effect! (:issue:`8068`)
* (macOS) Prevent collection of ``.DS_Store`` files, which might be present
  in build environment's package directories after user navigated them using
  the Finder app. (:issue:`8042`)
* (Windows) Fix marshal error at the start of binary dependency analysis,
  caused by inferred DLL search path ending up an instance of
  :class:`pathlib.Path` instead of :class:`str`. (:issue:`8081`)
* Bump the required ``packaging`` version to 22.0, which is required for
  proper handling of metadata that contains markers with ``extra``\ s.
  (:issue:`8061`)
* Fix erroneous DLL parent path preservation when :data:`sys.base_prefix`
  itself is a symbolic link. In such case, we need to exclude both
  resolved and unresolved path variant for ``sys.base_prefix``, in order to
  prevent either from ending up in the list of directories for which DLL
  parent paths are preserved. Failing to do so, for example, caused
  ``_ctypes`` failing to load in an application build on Windows with
  Python installed via ``scoop``, due to ``libffi-8.dll`` having spuriously
  preserved the parent directory path instead of being collected to top-level
  application directory. (:issue:`8023`)
* Fix matching of pre-release versions in
  :func:`PyInstaller.utils.hooks.check_requirement` and
  :func:`PyInstaller.utils.hooks.is_module_satisfies`. Both functions now
  match pre-release versions, which restores the behavior of the old
  ``pkg_resources``-based implementation from PyInstaller < 6.0
  that is implicitly expected by existing hooks. (:issue:`8093`)
* If the entry-point script has no suffix, append the ``.py`` suffix
  to the filename passed to the ``compile`` function when byte-compiling
  the script for collection. This ensures that the entry-point script
  filename never coincides with executable filename, especially in POSIX
  builds, where executables have no suffix either (and their name is based
  on the entry-point script basename by default). Entry-point script having
  the same filename as the executable causes issues when ``traceback``
  (and ``linecache``) try to access source code for it, an in the process
  end up reading the executable file if it happens to be in the current
  working directory. (:issue:`8046`)
* Improve speed of :func:`pkgutil.iter_modules` override, especially in cases
  when the function is called multiple times. (:issue:`8058`)
* Load PyInstaller hooks using :pep:`451` ``importlib.abc.Loader.exec_module``
  instead of deprecated :pep:`302` ``importlib.abc.Loader.load_module``.
  (:issue:`8031`)
* Prevent an attempt at relative import of a missing (optional) sub-module
  within a package (e.g., ``from .module import something``) from tricking
  the modulegraph/analysis into collecting an unrelated but eponymous
  top-level module. (:issue:`8010`)


Hooks
~~~~~

* Add hook for ``PySide6.QtGraphs`` that was introduced in ``PySide6`` 6.6.0.
  (:issue:`8021`)
* Add hooks for ``distutils.command.check`` and
  ``setuptools._distutils.command.check`` that prevent unnecessary
  collection of ``docutils`` (which in turn triggers collection of
  ``pygments``, ``PIL``, etc.). (:issue:`8053`)
* Deduplicate and sort the list of discovered/selected ``matplotlib``
  backends before displaying it in log messages, to avoid giving
  impression that they are collected multiple times. (:issue:`8009`)
* Update ``PySide6`` hooks for compatibility with ``PySide6`` 6.6.0 and
  python 3.12. (:issue:`8021`)


6.1.0 (2023-10-13)
------------------

Features
~~~~~~~~

* Allow users to re-enable the old onedir layout (without contents directory) by
  settings the :option:`--contents-directory` option (or the equivalent
  ``contents_directory`` argument to ``EXE`` in the .spec file) to ``'.'``.
  (:issue:`7968`)


Bugfix
~~~~~~

* (macOS) Prevent bootloader from clearing ``DYLD_*`` environment variables
  when running in ``onefile`` mode, in order to make behavior consistent
  with ``onedir`` mode. (:issue:`7973`)
* (Windows) Fix unintentional randomization of library search path order
  in the binary dependency analysis step. The incorrect order of search
  paths would result in defunct builds when using both ``pywin32``
  and ``PyQt5``, ``PyQt6``, ``PySide2``, or ``PySide6``, as it would prevent
  the python's copy of ``VCRUNTIME140_1.dll`` from being collected into
  the top-level application directory due to it being shadowed by the
  Qt-provided copy. Consequently, the application would fail with
  ``ImportError: DLL load failed while importing pywintypes: The specified
  module could not be found.`` (:issue:`7978`)
* Ensure that ``__main__`` is always in the list of modules to exclude,
  to prevent a program or a library that attempts to import ``__main__``
  from pulling PyInstaller itself into frozen application bundle.
  (:issue:`7956`)
* Fix :func:`PyInstaller.utils.hooks.collect_entry_point` so that it returns
  module names (without class names). This matches the behavior of previous
  PyInstaller versions that regressed in PyInstaller ``v6.0.0`` during
  transition from ``pkg_resources`` to ``importlib.metadata``. (:issue:`7958`)
* Fix ``TypeError: process_collected_binary() got an unexpected keyword
  argument 'strip'`` error when UPX compression is enabled. (:issue:`7998`)
* Validate binaries returned by analysis of ``ctypes`` calls in collected
  modules; the analysis might return files that are in ``PATH`` but are
  not binaries, which then cause errors during binary dependency analysis.
  An example of such problematic case is the ``gmsh`` package on Windows,
  where ``ctypes.util.find_library('gmsh')`` ends up resolving the python
  script called ``gmsh`` in the environment's Scripts directory.
  (:issue:`7984`)


Hooks
~~~~~

* Update ``PySide6.QtHttpServer`` hook for compatibility with ``PySide6``
  6.5.3 on Windows. (:issue:`7994`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* (macOS) Lower the severity of a missing ``Info.plist`` file in a
  collected macOS .framework bundle from an error to a warning (unless
  strict collection mode is enabled). While missing ``Info.plist`` in a
  collected .framework bundle will cause ``codesign`` to refuse to sign
  the generated .app bundle, the user might be interested in building
  just the POSIX application or may not plan to sign their .app bundle.
  Fixes building with old ``PyQt5`` PyPI wheels (< 5.14.1). (:issue:`7959`)


6.0.0 (2023-09-22)
------------------

Features
~~~~~~~~

* (macOS) PyInstaller now attempts to preserve the ``.framework`` bundles when
  collecting shared libraries from them. If a shared library is to be collected
  from a ``.framework`` bundle, the ``Info.plist`` is also automatically
  collected. The ``.framework`` bundle collection code also attempts to fix the
  bundles' structure to conform to code-signing requirements (i.e., creation of
  the ``Current`` symbolic link in the ``Versions`` directory, and top-level
  contents being symbolic links that point to counterparts in the
  ``Versions/Current`` directory). Note that other resources (for example from
  ``Resources`` or ``Helpers`` directories) still need to be explicitly
  collected by hooks. (:issue:`7619`)
* (macOS) The file relocation mechanism in ``BUNDLE`` that generates macOS .app
  bundles has been completely redesigned. All data files are now placed into
  directory structure rooted in ``Contents/Resources``, all shared libraries (as
  well as nested .framework bundles) are placed into directory structure rooted
  in ``Contents/Frameworks``, and only the the program executable is placed into
  the ``Contents/MacOS`` directory. The contents of ``Contents/Resources`` and
  ``Contents/Frameworks`` directories are cross-linked via symlinks between the
  two directory trees in order to maintain illusion of mixed-content directories
  (in both directory trees). The cross-linking is done at either file level or
  (sub)directory level, depending on the content type of a (sub)directory. For
  directories in ``Contents/Frameworks`` that contain a dot in the name, a
  work-around is automatically applied: the directory is created with a modified
  name that does not include the dot, and next to it, a symbolic link is created
  under the original name and pointing to the directory with modified name.
  (:issue:`7619`)
* (non-Windows) PyInstaller now attempts to preserve the parent directory
  structure for shared libraries discovered and collected by the binary
  dependency analysis, instead of automatically collecting them into the
  top-level application directory. Due to library search path assumptions
  made in various places, symbolic links to collected libraries are created
  in the top-level application directory. This complements earlier work
  (:issue:`7028`) that implemented DLL parent directory structure
  preservation on Windows. (:issue:`7619`)
* (Windows) Add an option to hide or minimize the console window in
  console-enabled applications, but only if the program's process owns
  the console window (i.e., the program was not launched from an existing
  console window). (:issue:`7729`)
* (Windows) The :option:`--add-data` and :option:`--add-binary` options accept
  the POSIX syntax of ``--add-data=source:dest`` rather than
  ``--add-data=source;dest``. The latter will continue to work on Windows to
  avoid breaking backwards compatibility but is discouraged in favour of the now
  cross platform format. (:issue:`6724`)
* Add automatic binary vs. data file (re)classification step to the analysis
  process. PyInstaller now inspects all files passed to ``Analysis`` via
  ``datas`` and ``binaries`` arguments, as well as all files returned by hooks
  via ``datas`` and ``binaries`` hook global variables. The inspection mechanism
  is platform-specific, and currently implemented for Windows, Linux, and macOS.
  Proper file classification ensures that all collected binary files undergo
  binary dependency analysis and any other platform-specific binary processing.
  On macOS, it also helps ensuring that the collected files are placed in the
  proper directory in the generated .app bundles. (:issue:`7619`)
* Add support for specifying hash randomization seed via ``hash_seed=<value>``
  :ref:`run-time option <specifying python interpreter options>` when building
  the application. This allows the application to use a fixed seed value or
  disable hash randomization altogether by using seed value of 0.
  (:issue:`7847`)
* Allow spec files to take custom command line parameters. See :ref:`adding
  parameters to spec files <spec_parameters>`. (:issue:`4482`)
* Extend the operation retry mechanism that was initially introduced by
  :issue:`7840` to cover all processing steps that are performed during
  assembly of a Windows executable. This attempts to mitigate the interference
  from anti-virus programs and other security tools, which may temporarily block
  write access to the executable for a scan between individual processing steps.
  (:issue:`7871`)
* Implement pass-through for `Python's X-options
  <https://docs.python.org/3/using/cmdline.html#cmdoption-X>`_ via PyInstaller's
  :ref:`run-time options mechanism <specifying python interpreter options>`.
  (:issue:`7847`)
* Implement support for creating symbolic links from special ``'SYMLINK'``
  TOC entries, either at build-time (``onedir`` mode) or at run-time
  (``onefile`` mode). Implement symbolic link preservation support in the
  analysis process; if a file and a symbolic link pointing to it are both to be
  collected, and if their relative relationship is preserved in the frozen
  application, the symbolic link is collected as a ``'SYMLINK'`` entry.
  (:issue:`7619`)
* Implement :func:`PyInstaller.utils.hooks.check_requirement` hook utility
  function as an :mod:`importlib.metadata`-based replacement for
  :func:`PyInstaller.utils.hooks.is_module_satisfies`; the latter is now
  just an alias for the former, kept for compatibility with existing hooks.
  (:issue:`7943`)
* Restructure onedir mode builds so that everything except the executable (and
  ``.pkg`` if you're using external PYZ archive mode) are hidden inside a
  sub-directory. This sub-directory's name defaults to ``_internal`` but may be
  configured with a new :option:`--contents-directory` option. Onefile
  applications and macOS ``.app`` bundles are unaffected. (:issue:`7713`)
* The :func:`PyInstaller.utils.hooks.collect_all` hook utility function now
  attempts to translate the given importable package name into distribution name
  before attempting to collect metadata. This allows the function to handle
  cases when the distribution name does not match the importable package name.
  (:issue:`7943`)


Bugfix
~~~~~~

* (macOS) ``QtWebEngine`` now works in ``onefile`` builds (previously available
  only in ``onedir`` builds). (:issue:`4361`)
* (macOS) Fix the shared library duplication problem where a shared library that
  is also referred to via its symbolic links (e.g., a shared library
  ``libwx_baseu-3.1.5.0.0.dylib`` with symbolic links
  ``libwx_baseu-3.1.5.dylib`` and ``libwx_baseu-3.0.dylib``) ends up collected
  as duplicates and consequently crashes the program. The symbolic links should
  now be preserved, thus avoiding the problem. (:issue:`5710`)
* (macOS) In generated .app bundles, the data files from ``PySide2``,
  ``PySide6``, ``PyQt5``, or ``PyQt6`` directory are now relocated to the
  directory structure rooted in ``Contents/Resources`` to ensure compliance with
  code-signing requirements. The content cross-linking between
  ``Contents/Resources`` and ``Contents/Frameworks`` should ensure that ``QML``
  components in the ``qml`` sub-directory continue to work in spite of plugins
  (shared libraries) being technically separated from their corresponding
  metadata files. The automatic work-around for directories with dots in names
  should prevent code-signing issues due to some ``QML`` components in Qt5
  having dot in their names (e.g. ``QtQuick.2`` and ``QtQuick/Controls.2``.
  (:issue:`7619`)
* (macOS) In generated .app bundles, the source .py files are now again
  relocated to ``Contents/Resources`` directory (and cross-linked into
  ``Contents/Frameworks``), which ensures that code-signing does not store
  signatures into the files' extended attributes. This reverts the exemption
  made in :issue:`7180` to accommodate the ``cv2`` loader script; the problem is
  now solved by cross-linking binaries from ``Contents/Frameworks`` to
  ``Contents/Resources``, which allows the loader to find the extension binary
  (or rather, a symbolic link to it) next to the .py file. (:issue:`7619`)
* (macOS) Sandboxing for ``QtWebEngine`` in ``PySide6`` and ``PyQt6`` is not
  disabled anymore by the corresponding run-time hooks (see :issue:`6903`), as
  it should work out-of-the-box thanks to PyInstaller now preserving the
  structure of the ``QtWebEngineCore.framework`` bundle. (:issue:`7619`)
* (macOS) The main process in a program that uses ``QtWebEngine`` is not
  mis-identified as ``QtWebEngineCore`` anymore in the application's menu bar.
  This applies to ``onedir`` POSIX program builds (i.e. the .app bundles were
  not affected by this). (:issue:`5409`)
* (Windows) Avoid aborting the build process if machine type (architecture)
  cannot be determined for a DLL in a candidate search path; instead, skip over
  such files, and search in other candidate paths. Fixes build errors when a
  search path contains an invalid DLL file (for example, a stub file).
  (:issue:`7874`)
* (Windows) Prevent PyInstaller's binary dependency analysis from looking for
  shared libraries in all :data:`sys.path` locations. Instead, search only
  :data:`sys.base_prefix` and ``pywin32`` directories, of available. This, for
  example, prevents PyInstaller from picking up incompatible DLLs from
  system-installed programs that happen to put their installation directory into
  system-wide :envvar:`PYTHONPATH`. (:issue:`5560`)
* (Windows) Remove the use of deprecated ``distutils.sysconfig`` module. The
  import of this module seems to cause the python process to crash when
  ``tensorflow`` is subsequently imported during import analysis.
  (:issue:`7347`)
* Fix file duplication when collecting a file and symbolic links pointing at it;
  with new symbolic link support, the symbolic links are now properly preserved.
  This should help reducing the size of builds made on Linux and macOS with
  Anaconda, which provides versioned symbolic links for packaged shared
  libraries, and PyInstaller tends to collect them all due to hook helper based
  on the packages' metadata. (:issue:`7619`)
* Fix incompatibility between PyInstaller's frozen importer
  (``PyiFrozenImporter``) and :mod:`importlib.resources` when trying to look up
  the resources of a collected namespace package via
  :func:`importlib.resources.files()`. (:issue:`7921`)
* When copying files into ``onedir`` application bundles, use
  :func:`shutil.copyfile` instead of :func:`shutil.copy2` to avoid issues
  with original permissions/metadata being too restrictive. (:issue:`7938`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (Linux) Removed support for building LSB-compliant bootloader, due to
  lack of support for LSB (Linux Standard Base) in contemporary linux
  distributions. (:issue:`7807`)
* (macOS) Due to relocation of all dynamic libraries into directory
  structure rooted in the ``Contents/Frameworks`` directory, the
  ``sys._MEIPASS`` variable as well as the ``os.path.dirname(__file__)``
  in the entry-point script now point to ``Contents/Frameworks`` instead of
  ``Contents/MacOS``, while ``os.path.dirname(sys.executable)`` continues
  to point to the ``Contents/MacOS`` directory. The behavior change applies
  only to ``onedir`` .app bundles (in ``onefile`` ones, ``sys._MEIPASS``
  and ``__file__`` of the entry-point script have always pointed to the
  temporary extraction directory and continue to do so). (:issue:`7619`)
* (macOS) The changes made to the macOS .app bundle generation code and the
  resulting .app bundle structure (strict relocation of binaries to
  ``Contents/Frameworks`` and data files to ``Contents/Resources``,
  bi-directional cross-linking between ``Contents/Frameworks`` and
  ``Contents/Resources``, preservation of nested .framework bundles,
  automatic work-around for dots in directory names) are likely
  incompatible with existing (external) post-processing scripts.
  (:issue:`7619`)
* (Windows) Removed command-line options related to processing of the
  WinSxS assemblies: ``--win-private-assemblies`` and
  ``--win-no-prefer-redirects``.
  The corresponding arguments to ``Analysis`` are deprecated and raise and
  error if set to ``True``. (:issue:`7784`)
* (Windows) Removed support for analyzing and collection of dependencies
  referenced via WinSxS (side-by-side) assemblies. This affects binaries
  compiled with Visual Studio 2008 and earlier, as VC9 run-time was the
  last version to make use of WinSxS. If you require support for such
  binaries and you need referenced WinSxS binaries collected with your
  application, use older version of PyInstaller. (:issue:`7784`)
* (Windows) Removed support for external application manifest in onedir
  builds. Removed the ``--no-embed-manifest`` command-line option and
  deprecated the corresponding ``embed_manifest`` argument to ``EXE``
  to raise an error if set to ``False``. (:issue:`7784`)
* All of onedir build's contents except for the executable are now moved into a
  sub-directory (called ``_internal`` by default). ``sys._MEIPASS`` is adjusted
  to
  point to this ``_internal`` directory. The breaking implications for this
  are:

  * Assumptions that ``os.path.dirname(sys.executable) == sys._MEIPASS`` will
    break. Code locating application resources using
    ``os.path.dirname(sys.executable)`` should be adjusted to use ``__file__``
    or ``sys._MEIPASS`` and any code locating the original executable using
    ``sys._MEIPASS`` should use :data:`sys.executable` directly.

  * Any custom post processing steps (either in the ``.spec`` file or
    externally) which modify the bundle will likely need adjusting to
    accommodate the new directory. (:issue:`7713`)
* PyInstaller-frozen applications are not affected by the :envvar:`PYTHONUTF8`
  environment variable anymore. To permanently enable or disable the UTF8 mode,
  use the ``X utf8_mode=1`` or ``X utf_mode=0`` :ref:`run-time option
  <specifying python interpreter options>` when building the application.
  (:issue:`7847`)
* Remove bytecode encryption (``--key`` and ``cipher`` options).
  (:issue:`6999`)
* Remove the ``--ascii`` command-line option, which is an effective no-op under
  python 3; the :mod:`codecs` module is always collected due to being listed
  among the base modules. (:issue:`7801`)
* Remove the built-in attempt at collection of data files from packages
  that are installed as python eggs. Collection of all non-python resources
  from packages should be handled in the standardized way via hooks,
  regardless of how a package is installed. (:issue:`7784`)
* Remove support for zipped eggs. PyInstaller will not collect python code nor
  resources from zipped eggs, nor will it collect zipped eggs as a whole.
  (:issue:`7784`)
* Remove the ``requirements_for_package`` hook utility function, which was
  primarily used by :func:`~PyInstaller.utils.hooks.collect_all`; the latter
  does not include the top-level modules of metadata-declared requirements among
  the returned hidden imports anymore. (:issue:`7943`)
* The :func:`PyInstaller.utils.hooks.collect_data_files` hook utility helper
  does not collect ``.pyc`` files from ``__pycache__`` directories anymore, even
  with ``include_py_files=True`` argument. (:issue:`7943`)
* The :func:`PyInstaller.utils.hooks.is_module_satisfies` helper does not
  support the ``version`` and ``version_attribute`` arguments anymore; the
  function will raise an error if they are specified. If the distribution
  specified in the ``requirements`` string is not found, the function will not
  attempt to import the eponymous module and read its version attribute anymore.
  (:issue:`7943`)
* The collection of "py files", enabled by the ``include_py_files=True``
  argument to the :func:`PyInstaller.utils.hooks.collect_data_files` hook
  utility function, is now restricted to only ``.py`` and ``.pyc`` files.
  Previously, all suffices from :func:`importlib.machinery.all_suffixes` were
  enabled, which resulted in spurious collection of dynamic libraries and
  extensions (due to ``.so``, ``.abi3.so``, ``.pyd``, etc. being among those
  suffices). (:issue:`7943`)


Bootloader
~~~~~~~~~~

* (Linux, macOS) When extracting files from ``onefile`` archive, the
  executable bit is now set only on binaries (files whose TOC type code
  was either ``BINARY``, ``EXECUTABLE``, or ``EXTENSION``) or data files
  that originally had the executable bit set. Therefore, binaries are now
  extracted with permissions bits set to ``0700``, while all other files
  have permissions bits set to ``0600``. (:issue:`7950`)
* Use `PEP 587 Python Initialization Configuration API
  <https://peps.python.org/pep-0587>`_ to configure the embedded Python
  interpreter. (:issue:`7847`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* (Windows) The temporary/intermediate executable files are not generated
  with ``.notanexecutable`` suffix anymore, as the retry mechanism from
  :issue:`7840` and :issue:`7871` is now the preferred way of dealing with
  anti-virus program interference during the build. (:issue:`7871`)
* Avoid collecting ``pathlib`` and ``tokenize`` (and their dependencies,
  such as ``urllib``) into ``base_library.zip``. By collecting them into
  PYZ archive, only submodules that the application really requires can
  be collected, which helps reducing the size of applications that, for
  example, do not require the full ``urllib`` package. (:issue:`7836`)
* Drop support for end of life Python 3.7. (:issue:`7733`)


Bootloader build
~~~~~~~~~~~~~~~~

* To enable the passing of extra arguments to the bootloader compiler during
  installation via pip,
  you can utilize the environment variable ``PYINSTALLER_BOOTLOADER_WAF_ARGS``.
  However,
  it is essential to ensure that the environment variable
  ``PYINSTALLER_COMPILE_BOOTLOADER``
  is present for this functionality to work correctly. (:issue:`7796`)


5.13.2 (2023-08-29)
-------------------

Bugfix
~~~~~~

* (Windows) Fix ``OSError: exception: access violation reading 0x00000010``
  raised by ``matplotlib`` and ``win32com`` run-time hooks when ran in 32-bit
  frozen application (regression introduced in ``v5.13.1``). (:issue:`7893`)


Hooks
~~~~~

* Fix the license of the new ``_pyi_rth_utils`` run-time package; it is
  now licensed under permissive Apache license, which matches the license
  of the run-time hooks that use this run-time package. (:issue:`7894`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Fix the license of the ``pyi_splash`` run-time module; it is now licensed
  under permissive Apache license to avoid unintentionally imposing
  additional license restrictions on the frozen applications that make
  use of this module. (:issue:`7896`)


5.13.1 (2023-08-26)
-------------------

Security
~~~~~~~~

* (Windows) Ensure that the access to temporary directories created by the
  ``matplotlib`` and ``win32com`` run-time hooks is restricted to the user
  running the frozen application, even if the directory in the ``TMP`` or
  ``TEMP`` variables points to a system-wide *world writable* location that can
  be accessed by all users. (:issue:`7827`)


Bugfix
~~~~~~

* (macOS) Fix :func:`pkgutil.iter_modules` failing to find submodules of a
  package that contains data files when running as a macOS .app bundle.
  (:issue:`7884`)
* (Windows) Fix ``win32com`` run-time hook to fully isolate the ``gen_py``
  cache. This prevents access to the global cache, which results in errors when
  the global cache contains some, but not all, required modules. (:issue:`6257`)
* (Windows) Fix splash screen not being able to locate collected Tk resources in
  onefile applications created in MSYS2 python environment. (:issue:`7828`)
* (Windows) Fixed bug where GdkPixbuf loaders.cache dll paths are absolute paths
  (e.g. ``C:/tools/msys64/mingw64/lib/gdk-pixbuf-2.0/2.10.0/loaders/*.dll``) and
  not relative paths (e.g.
  ``lib\\gdk-pixbuf\\loaders\\libpixbufloader-png.dll``) when the file is
  generated in the MSYS2/mingw64 environment. This results in the program
  crashing when run on another Windows machine because it cannot find the
  GdkPixbuf loader DLLs. (:issue:`7842`)
* Exclude NVIDIA graphics driver libraries from vendoring. (:issue:`7746`)
* Fix error handling in Glib schema compilation helper function. Ignore
  character encoding errors when reading stdout/stderr from
  ``glib-schema-compile`` process; this fixes errors in MSYS2/mingw64
  environment, caused by ``U+201C`` and ``U+201D`` quotation marks in the
  output. (:issue:`7833`)
* Implement a work-around for un-initialized ``sys._stdlib_dir`` and ensure that
  python-frozen stdlib modules in Python >= 3.11 have ``__file__`` attribute
  set. (:issue:`7847`)


Hooks
~~~~~

* Add support for commercial PyQt5 and PyQt6 wheels. (:issue:`7770`)


Bootloader
~~~~~~~~~~

* Have bootloader call :c:func:`Py_GetPath` before :c:func:`Py_SetPath` on all
  platforms (instead of just on Windows) to work around memory-initialization
  issues in python 3.8 and 3.9, which come to light with
  :envvar:`PYTHONMALLOC=debug <PYTHONMALLOC>` or :envvar:`PYTHONDEVMODE=1
  <PYTHONDEVMODE>` being set in the environment. (:issue:`7790`)


5.13.0 (2023-06-24)
-------------------

Features
~~~~~~~~

* Add support for Python 3.12. (:issue:`7670`)
* (Windows) Add support for collecting .pyc files from the ``python3X.zip``
  archive where ``Windows embeddable package`` Python stores its stdlib modules.
  (:issue:`4989`)


Bugfix
~~~~~~

* Limit the import of collected packages prior to performing binary
  dependency analysis to only Windows, where it is actually useful.
  On non-Windows platforms, there is no benefit to it, and it might
  cause issues with particular orders of package imports. (:issue:`7698`)
* When building PKG for ``onedir`` build, ensure that ``DATA`` entries
  are put into dependencies list instead of including them in the PKG.
  This complements existing behavior for ``BINARY`` and ``EXTENSION``
  entries, and prevents a ``onedir`` build from becoming a broken
  ``onefile`` one if user accidentally passes binaries and data files
  TOCs to ``EXE`` instead of `COLLECT` when manually editing the
  spec file. (:issue:`7708`)


5.12.0 (2023-06-08)
-------------------

Features
~~~~~~~~

* (macOS) PyInstaller now removes all rpaths from collected binaries
  and replaces them with a single rpath pointing to the top-level
  application directory, relative to ``@loader_path``. (:issue:`7664`)
* Attempt to preserve the parent directory layout for ``pywin32``
  extensions that originate from ``win32`` and ``pythonwin`` directories,
  instead of collecting those extensions to top-level application directory.
  (:issue:`7627`)


Bugfix
~~~~~~

* (Linux/macOS) Fix the Qt directory path override in ``PySide2`` and
  ``PySide6`` run-time hooks. These paths, set via ``QT_PLUGIN_PATH`` and
  ``QML2_IMPORT_PATH`` environment variables, are used with ``PySide2``
  and ``PySide6`` builds that that use system-wide Qt installation and
  are not portable by default (e.g. Homebrew). (:issue:`7649`)
* (macOS) When rewriting the dylib identifier and paths to linked
  libraries in a collected binary, instead of directly using
  ``@loader_path``-based path, use ``@rpath``-based path and replace
  rpaths in the binary with a single rpath that points to the top-level
  application directory, relative to ``@loader_path``. This ensures that
  the library identifiers of collected shared libraries and their
  references in referring binaries always match, which allows packages
  to pre-load a library from an arbitrary location via for example
  ``ctypes``. (:issue:`7664`)
* (Windows) Fix string serialization of ``VSVersionInfo`` to account for
  the possibility of ``StringStruct`` values containing quote characters.
  (:issue:`7630`)
* Attempt to fix compatibility of PyInstaller's ``PyiFrozenImporter`` with
  ``importlib.util.LazyLoader``. (:issue:`7657`)
* Attempt to mitigate issues with Anaconda ``pywin32`` package that
  result from the package installing three copies of ``pywintypes3X.dll``
  and ``pythoncom3X.dll`` in different locations. (:issue:`7627`)
* Changes made to ``datas`` and ``binaries`` lists that are passed to
  ``Analysis`` constructor will now invalidate the cached ``Analysis``
  and trigger a re-build. This applies both to changes made by editing
  the .spec file manually and to automatic changes due to addition or
  removal of corresponding command-line options (:option:`--add-data`,
  :option:`--add-binary`, :option:`--collect-data`,
  :option:`--collect-binaries`, :option:`--copy-metadata`).
  Previously, changes might not have taken effect as the old cached build
  was returned if available and unless user explicitly requested a clean
  build using the :option:`--clean` command-line option. (:issue:`7653`)
* Ensure that ``qt_{lang}`` translation files are collected with the
  ``QtCore`` module, in addition to already-collected ``qtbase_{lang}``
  files. Applies to all four Qt-bindings: ``PySide2``, ``PySide6``,
  ``PyQt5``, and ``PyQt6``. (:issue:`7682`)
* Fix ``ModuleNotFoundError: No module named 'ipaddress'`` for any application
  built with Python >=3.11.4. (:issue:`7692`)
* Fix splash-enabled program crashing due to NULL-pointer dereference
  in the bootloader when the Tcl/Tk shared libraries cannot be loaded.
  The program should now run the user's python code, where it will
  raise an exception if the ``pyi_splash`` module is used. (:issue:`7679`)
* Implement proper binary dependency scanning in the ``SPLASH`` target,
  so that binary dependencies of the Tcl and Tk shared libraries are
  always collected and added to the list of splash requirements
  (for pre-extraction in onefile builds). This fixes the splash screen
  when building with Windows build of python.org Python 3.12b1, which
  ships Tcl shared library with new dependency on ``zlib1.dll``.
  (:issue:`7679`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* (macOS) Use macOS-provided ``install_name_tool`` utility to modify headers
  on collected binaries: change the dylib identifier to
  ``@rpath/<name>.dylib``,
  rewrite paths to linked non-system shared libraries to
  ``@rpath/<dependency>``,
  remove any additional rpaths and add an rpath pointing to the application's
  top-level directory, relative to the ``@loader_path``. Previously, the
  header modification was performed using ``macholib`` and was limited
  only to modification of dylib identifier and paths to linked non-system
  shared libraries. (:issue:`7664`)


5.11.0 (2023-05-13)
-------------------

Features
~~~~~~~~

* Add a work-around for pure-python modules that do not specify encoding via
  :pep:`263` encoding header but contain non-ASCII characters in local
  (non-UTF8) encoding. When such characters are present only in code comments,
  python still loads and runs the module, but attempting to retrieve its source
  code via the loader's ``get_source()`` method results in a
  :class:`UnicodeDecodeError`, which interrupts the analysis process. The error
  is now caught and a fall-back codepath attempts to retrieve the source code as
  raw data to avoid encoding issues. (:issue:`7622`)


Bugfix
~~~~~~

* (Windows) Avoid writing collected binaries to binary cache unless
  they need to be processed (i.e., only if binary stripping or ``upx``
  processing is enabled). (:issue:`7595`)
* Fix a regression in bootloader that caused crash in onefile executables
  when encountering a duplicated entry in the PKG/CArchive and the
  ``PYINSTALLER_STRICT_UNPACK_MODE`` environment variable not being set.
  (:issue:`7613`)


Deprecations
~~~~~~~~~~~~

* The ``TOC`` class is now deprecated; use a plain ``list`` with the same
  three-element tuples instead. PyInstaller now performs explicit
  normalization (i.e., entry de-duplication) of the TOC lists passed
  to the build targets (e.g., ``PYZ``, ``EXE``, ``COLLECT``) during their
  instantiation. (:issue:`7615`)


Bootloader
~~~~~~~~~~

* Fix bootloader building with old versions of ``gcc`` that do not
  support the ``-Wno-error=unused-but-set-variable`` compiler flag
  (e.g., ``gcc`` v4.4.3). (:issue:`7592`)


Documentation
~~~~~~~~~~~~~

* Update the documentation on TOC lists and ``Tree`` class to reflect the
  deprecation of the ``TOC`` class. (:issue:`7615`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Remove the use of the ``TOC`` class in the analysis / build process,
  and use plain ``list`` instances instead. The implicit normalization
  (de-duplication) of TOC entries performed by the ``TOC`` class has been
  replaced with explicit normalization. The TOC lists produced by ``Analysis``
  are explicitly normalized at the end of Analysis instantiation, before
  they are stored in the Analysis properties (e.g., ``Analysis.pure``,
  ``Analysis.binaries``, ``Analysis.datas``). Similarly, the TOC lists
  passed to the build targets (e.g., ``PYZ``, ``EXE``, ``COLLECT``) are
  explicitly normalized as part of the targets' instantiation process.
  (:issue:`7615`)


5.10.1 (2023-04-14)
-------------------

Bugfix
~~~~~~

* Fix regression on platforms with strict data alignment requirements (such as
  linux on ``armhf``/``armv7``), caused by bug in PKG/CArchive generation that
  was introduced during the archive writer code cleanup. The regression caused
  executable to terminate with ``Bus error`` on the affected platforms, such as
  32-bit Debian Buster on Raspberry Pi 4. (:issue:`7566`)


5.10.0 (2023-04-11)
-------------------

Bugfix
~~~~~~

* (Linux) Ignore the executable name resolution based on ``/proc/self/exe``
  when the PyInstaller-frozen executable is launched via the ``ld.so``
  dynamic loader executable. In such cases, the resolved name points to
  the ``ld.so`` executable, causing the PyInstaller-frozen executable to
  fail with *Cannot open PyInstaller archive from executable...* error.
  (:issue:`7551`)
* Ensure that binaries that are manually specified in the .spec file (or via
  corresponding :option:`--add-binary` or :option:`--collect-binaries`
  command-line switches) undergo the binary dependency analysis, so their
  dependencies are automatically collected. (:issue:`7522`)
* Extend the ``excludedimports`` mechanism rework from :issue:`7066`
  to properly handle relative imports within the package. For example,
  ensure that ``excludedimports = ['a.b']`` within the hook for package
  ``a`` takes effect when package ``a`` does ``from . import b`` (in
  addition to ``from a import b``). (:issue:`7495`)
* Extend the ``excludedimports`` mechanism rework from :issue:`7066`
  to properly handle the case of multiple submodules being imported in a
  single ``from ... import ...`` statement (using absolute or relative import).
  For example, when package ``c`` does ``from d import e, f``, we need to
  consider potential ``excludedimports`` rules matching package ``d`` and,
  if ``d`` itself is not excluded, potential rules individually matching
  ``d.e`` and ``d.f``. (:issue:`7495`)
* Fix marshal error in binary dependency search stage, caused by the list of
  collected packages containing a ``modulegraph.Alias`` instance instead of only
  plain :class:`str` instances. (:issue:`7515`)
* Reorganize the ``multiprocessing`` run-time hook to override ``Popen``
  implementations only for ``spawn`` and ``forkserver`` start methods,
  but not for the ``fork`` start method. This avoids a dead-lock when
  attempting to perform nested multiprocessing using the ``fork`` start
  method, which occurred due to override-provided lock (introduced in
  :issue:`7411`) being copied in its locked state into the forked
  sub-process. (:issue:`7494`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* The ``archive_viewer`` utility has been rewritten with modified
  command-line interface (``--log`` has been renamed to ``--list``) and
  with changed output formatting. (:issue:`7518`)


Hooks
~~~~~

* (Windows) Improve support for ``matplotlib >= 3.7.0`` by collecting all
  ``delvewheel``-generated files from the ``matplotlib.libs`` directory,
  including the load-order file. This is required when PyPI ``matplotlib``
  wheels are used in combination with Anaconda python 3.8 and 3.9.
  (:issue:`7503`)
* Add hook for ``PyQt6.QtSpatialAudio`` module, which was added in
  ``PyQt6`` 6.5.0. (:issue:`7549`)
* Add hook for ``PyQt6.QtTextToSpeech`` module, which was added in
  ``PyQt6`` 6.4 series. (:issue:`7549`)
* Extend ``PySide6`` hooks for ``PySide6`` 6.5.0 compatibility: add hooks
  for ``QtLocation``, ``QtTextToSpeech``, and ``QtSerialBus`` modules
  that were introduced in ``PySide`` 6.5.0. (:issue:`7549`)


Documentation
~~~~~~~~~~~~~

* Clarify the supported color specification formats and apply consistent
  formatting of default parameter values in the splash screen documentation.
  (:issue:`7529`)


5.9.0 (2023-03-13)
------------------

Features
~~~~~~~~

* Choose :ref:`hooks provided by packages <provide hooks with package>` over
  hooks from
  `pyinstaller-hooks-contrib <https://github.com/pyinstaller/pyinstaller-hooks-contrib/>`_
  if both provide the same hook. (:issue:`7456`)


Bugfix
~~~~~~

* Fix changes to :data:`sys.path` made in the spec file being ignored by hook
  utility functions (e.g. :func:`~PyInstaller.utils.hooks.collect_submodules`).
  (:issue:`7456`)


5.8.0 (2023-02-11)
------------------

Features
~~~~~~~~

* Compile the collected GLib schema files using ``glib-schema-compiler``
  instead of collecting the pre-compiled ``gschemas.compiled`` file, in
  order to properly support collection of schema files from multiple
  locations. Do not collect the source schema files anymore, as only
  ``gschemas.compiled`` file should be required at run time. (:issue:`7394`)


Bugfix
~~~~~~

* (Cygwin) Avoid using Windows-specific codepaths that require
  ``pywin32-ctypes`` functionality that is not available in Cygwin
  environment. (:issue:`7382`)
* (non-Windows) Fix race condition in environment modification done by
  ``multiprocessing`` runtime hook when multiple threads concurrently
  spawn processes using the ``spawn`` method. (:issue:`7410`)
* (Windows) Changes in the version info file now trigger rebuild of the
  executable file. (:issue:`7338`)
* Disallow empty source path in the ``binaries`` and ``datas`` tuples
  that are returned from the hooks and sanitized in the
  ``PyInstaller.building.utils.format_binaries_and_datas``. The empty
  source path is usually result of an error in the hook's path retrieval
  code, and causes implicit collection of the whole current working
  directory. This is never the intended behavior, so raise a ``SystemExit``.
  (:issue:`7384`)
* Fix *unknown log level* error raised with ``--log-level=DEPRECATION``.
  (:issue:`7413`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* The deprecated ``PEP-302`` ``find_module()`` and ``load_module()``
  methods have been removed from PyInstaller's ``FrozenImporter``. These
  methods have not been used by python's import machinery since
  python 3.4 and ``PEP-451``, and were effectively left untested and
  unmaintained. The removal affects 3rd party code that still relies
  on ``PEP-302`` finder/loader methods instead of the ``PEP-451`` ones.
  (:issue:`7344`)


Hooks
~~~~~

* Collect ``multimedia`` plugins that are required by ``QtMultimedia``
  module starting with Qt6 v6.4.0. (:issue:`7352`)
* Do not collect ``designer`` plugins as part of ``QtUiTools`` module in
  ``PySide2`` and ``PySide6`` bindings. Instead, tie the collection of
  plugins only to the ``QtDesigner`` module. (:issue:`7322`)


Module Loader
~~~~~~~~~~~~~

* Remove deprecated ``PEP-302`` functionality from ``FrozenImporter``.
  The ``find_module()`` and ``load_module()`` methods are deprecated
  since python 3.4 in favor of ``PEP-451`` loader. (:issue:`7344`)


5.7.0 (2022-12-04)
------------------

Features
~~~~~~~~

* Add the package's location and exact interpreter path to the error message
  for
  the check for obsolete and PyInstaller-incompatible standard library
  back-port
  packages (``enum34`` and ``typing``). (:issue:`7221`)
* Allow controlling the build log level (:option:`--log-level`) via a
  ``PYI_LOG_LEVEL`` environment variable. (:issue:`7235`)
* Support building native ARM applications for Windows. If PyInstaller is ran
  on
  an ARM machine with an ARM build of Python, it will prodice an ARM
  application. (:issue:`7257`)


Bugfix
~~~~~~

* (Anaconda) Fix the ``PyInstaller.utils.hooks.conda.collect_dynamic_libs``
  hook utility function to collect only dynamic libraries, by introducing
  an additional type check (to exclude directories and symbolic links to
  directories) and additional suffix check (to include only files whose
  name matches the following patterns: ``*.dll``, ``*.dylib``, ``*.so``,
  and ``*.so.*``). (:issue:`7248`)
* (Anaconda) Fix the problem with Anaconda python 3.10 on linux and macOS,
  where all content of the environment's ``lib`` directory would end up
  collected as data  due to additional symbolic link pointing from
  ``python3.1``
  to ``python3.10``. (:issue:`7248`)
* (GNU/Linux) Fixes an issue with gi shared libraries not being packaged if
  they don't
  have version suffix and are in a special location set by ``LD_LIBRARY_PATH``
  instead of
  a typical library path. (:issue:`7278`)
* (Windows) Fix the problem with ``windowed`` frozen application being unable
  to spawn interactive command prompt console via ``subprocess`` module due
  to interference of the ``subprocess`` runtime hook with stream handles.
  (:issue:`7118`)
* (Windows) In ``windowed``/``noconsole`` mode, stop setting ``sys.stdout``
  and ``sys.stderr`` to custom ``NullWriter`` object, and instead leave
  them at ``None``. This matches the behavior of windowed python interpreter
  (``pythonw.exe``) and prevents interoperability issues with code that
  (rightfully) expects the streams to be either ``None`` or objects that
  are fully compatible with ``io.IOBase``. (:issue:`3503`)
* Ensure that ``PySide6.support.deprecated`` module is collected for
  ``PySide6`` 6.4.0 and later in order to enable continued support for
  ``|`` and ``&`` operators between Qt key and key modifier enum values
  (e.g., ``QtCore.Qt.Key_D`` and ``QtCore.Qt.AltModifier``). (:issue:`7249`)
* Fix potential duplication of python extension modules in ``onefile``
  builds, which happened when an extension was collected both as an
  ``EXTENSION`` and as a ``DATA`` (or a ``BINARY``) TOC type. This
  resulted in run-time warnings about files already existing; the
  most notorious example being ``WARNING: file already exists but
  should not:
  C:\Users\user\AppData\Local\Temp\MEI1234567\torch\_C.cp39-win_amd64.pyd``
  when building ``onefile`` applications that use ``torch``. (:issue:`7273`)
* Fix spurious attempt at reading the ``top_level.txt`` metadata from
  packages installed in egg form. (:issue:`7086`)
* Fix the log level (provided via :option:`--log-level`) being ignored by some
  build steps. (:issue:`7235`)
* Fix the problem with ``MERGE`` not properly cleaning up passed
  ``Analysis.binaries`` and ``Analysis.datas`` TOCs due to changes made to
  ``TOC`` class in PyInstaller 5.0. This effectively broke the supposed
  de-duplication functionality of ``MERGE`` and multi-package bundles,
  which should be restored now. (:issue:`7273`)
* Prevent ``$pythonprefix/bin`` from being added to :data:`sys.path` when
  PyInstaller is invoked using ``pyinstaller your-code.py`` but not using
  ``python -m PyInstaller your-code.py``. This prevents collection mismatch
  when
  a library has the same name as console script. (:issue:`7120`)
* Prevent isolated-subprocess calls from indefinitely blocking in their
  clean-up codepath when the subprocess fails to exit. After the grace
  period of 5 seconds, we now attempt to terminate such subprocess in
  order to prevent hanging of the build process. (:issue:`7290`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (Windows) In ``windowed``/``noconsole`` mode, PyInstaller does not set
  ``sys.stdout`` and ``sys.stderr`` to custom ``NullWriter`` object anymore,
  but leaves them at ``None``. The new behavior matches that of the windowed
  python interpreter (``pythonw.exe``), but may break the code that uses
  ``sys.stdout`` or ``sys.stderr`` without first checking that they are
  available. The code intended to be run frozen in ``windowed``/``noconsole``
  mode should be therefore be validated using the windowed python interpreter
  to catch errors related to console being unavailable. (:issue:`7216`)


Deprecations
~~~~~~~~~~~~

* Deprecate bytecode encryption (the ``--key`` option), to be removed in
  PyInstaller v6.0. (:issue:`6999`)


Hooks
~~~~~

* (Windows) Remove the ``subprocess`` runtime hook. The problem with invalid
  standard stream handles, which caused the ``subprocess`` module raise an
  ``OSError: [WinError 6] The handle is invalid`` error in a ``windowed``
  ``onefile`` frozen application when trying to spawn a subprocess without
  redirecting all standard streams, has been fixed in the bootloader.
  (:issue:`7182`)
* Ensure that each ``Qt*`` submodule of the ``PySide2``, ``PyQt5``,
  ``PySide6``,
  and ``PyQt6`` bindings has a corresponding hook, and can therefore been
  imported in a frozen application on its own. Applicable to the latest
  versions of packages at the time of writing: ``PySide2 == 5.15.2.1``,
  ``PyQt5 == 5.15.7``, ``PySide6 == 6.4.0``, and ``PyQt6 == 6.4.0``.
  (:issue:`7284`)
* Improve compatibility with contemporary ``Django`` 4.x version by removing
  the override of ``django.core.management.get_commands`` from the ``Django``
  run-time hook. The static command list override is both outdated (based on
  ``Django`` 1.8) and unnecessary due to dynamic command list being properly
  populated under contemporary versions of ``PyInstaller`` and ``Django``.
  (:issue:`7259`)
* Introduce additional log messages to ``matplotlib.backend`` hook to
  provide better insight into what backends are selected and why when the
  detection of ``matplotlib.use`` calls comes into effect. (:issue:`7300`)


Bootloader
~~~~~~~~~~

* (Windows) In a ``onefile`` application, avoid passing invalid stream handles
  (the ``INVALID_HANDLE_VALUE`` constant with value ``-1``) to the launched
  application child process when the standard streams are unavailable (for
  example, in a windowed/no-console application). (:issue:`7182`)


Bootloader build
~~~~~~~~~~~~~~~~

* Support building ARM native binaries using MSVC using the command
  ``python waf --target-arch=64bit-arm all``. If built on an ARM machine,
  ``--target-arch=64bit-arm`` is the default. (:issue:`7257`)
* Windows ARM64 bootloaders may now be built using an ARM build of clang with
  ``python waf --target-arch=64bit-arm --clang all``. (:issue:`7257`)


5.6.2 (2022-10-31)
-------------------

Bugfix
~~~~~~

* (Linux, macOS) Fix the regression in shared library collection, where
  the shared library would end up collected under its fully-versioned
  .so name (e.g., ``libsomething.so.1.2.3``) instead of its originally
  referenced name (e.g., ``libsomething.so.1``) due to accidental
  symbolic link resolution. (:issue:`7189`)


5.6.1 (2022-10-25)
-------------------

Bugfix
~~~~~~

* (macOS) Fix regression in macOS app bundle signing caused by a typo made
  in :issue:`7180`. (:issue:`7184`)


5.6 (2022-10-23)
-----------------

Features
~~~~~~~~

* Add official support for Python 3.11. (Note that PyInstaller v5.5 is also
  expected to work but has only been tested with a pre-release of Python 3.11.)
  (:issue:`6783`)
* Implement a new hook utility function,
  :func:`~PyInstaller.utils.hooks.collect_delvewheel_libs_directory`,
  intended for dealing with external shared library in ``delvewheel``-enabled
  PyPI
  wheels for Windows. (:issue:`7170`)


Bugfix
~~~~~~

* (macOS) Fix OpenCV (``cv2``) loader error in generated macOS .app
  bundles, caused by the relocation of package's source .py files.
  (:issue:`7180`)
* (Windows) Improve compatibility with ``scipy`` 1.9.2, whose Windows wheels
  switched to ``delvewheel``, and therefore have shared libraries located in
  external .libs directory. (:issue:`7168`)

* (Windows) Limit the DLL parent path preservation behavior from :issue:`7028`
  to files collected from site-packages directories (as returned by
  :func:`site.getsitepackages` and :func:`site.getusersitepackages`) instead of all
  paths in :data:`sys.path`, to avoid unintended behavior in corner cases, such as
  :data:`sys.path` containing the drive root or user's home directory.
  (:issue:`7155`)

* Fix compatibility with ``PySide6`` 6.4.0, where the deprecated
  ``Qml2ImportsPath`` location key is not available anymore; use the
  new ``QmlImportsPath`` key when it is available. (:issue:`7164`)
* Prevent PyInstaller runtime hook for ``setuptools`` from attempting to
  override ``distutils`` with ``setuptools``-provided version when
  ``setuptools`` is collected and its version is lower than 60.0. This
  both mimics the unfrozen behavior and prevents errors on versions
  between 50.0 and 60.0, where we do not explicitly collect
  ``setuptools._distutils``. (:issue:`7172`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (macOS) In generated macOS .app bundles, the collected source .py files
  are not relocated from ``Contents/MacOS`` to ``Contents/Resources``
  anymore, to avoid issues when the path to a .py file is supposed to
  resolve to the same directory as adjacent binary extensions. On the
  other hand, this change might result in regressions w.r.t. bundle
  signing and/or notarization. (:issue:`7180`)


Bootloader
~~~~~~~~~~

* (Windows) Update the bundled ``zlib`` sources to v1.2.13. (:issue:`7166`)


5.5 (2022-10-08)
-----------------

Features
~~~~~~~~

* (Windows) Support embedding multiple icons in the executable. (:issue:`7103`)


Bugfix
~~~~~~

* (Windows) Fix a regression introduced in PyInstaller 5.4 (:issue:`#6925`),
  where incorrect copy of ``python3.dll`` (and consequently an additional,
  incorrect copy of ``python3X.dll`` from the same directory) is collected
  when additional python installations are present in ``PATH``. (:issue:`7102`)
* (Windows) Provide run-time override for ``ctypes.util.find_library`` that
  searches ``sys._MEIPASS`` in addition to directories specified in ``PATH``.
  (:issue:`7097`)
* Fix the problem with ``pywin32`` DLLs not being found when importing
  ``pywin32`` top-level extension modules, caused by the DLL directory
  structure preservation behavior introduced in :issue:`7028`. Introduce
  a new bootstrap/loader module that adds the ``pywin32_system32``
  directory, if available, to both ``sys.path`` and the DLL search paths,
  in lieu of having to provide a runtime hook script for every single
  top-level extension module from ``pywin32``. (:issue:`7110`)


Hooks
~~~~~

* Fix an error raised by the ``matplotlib.backends`` hook when trying to
  specify the list of backends to collect via the hooks configuration.
  (:issue:`7091`)


5.4.1 (2022-09-11)
-------------------

Bugfix
~~~~~~

* (Windows) Fix run-time error raised by ``pyi_rth_win32comgenpy``, the
  run-time
  hook for ``win32com``. (:issue:`7079`)


5.4 (2022-09-10)
-----------------

Features
~~~~~~~~

* (Windows) When collecting a DLL that was discovered via link-time
  dependency analysis of a collected binary/extension, attempt to preserve
  its parent directory structure instead of collecting it into application's
  top-level directory. This aims to preserve the parent directory structure
  of DLLs bundled with python packages in PyPI wheels, while the DLLs
  collected from system directories (as well as from ``Library\bin``
  directory of the Anaconda's environment) are still collected into
  top-level application directory. (:issue:`7028`)
* Add support for ``setuptools``-provided ``distutils``, available since
  ``setuptools >= 60.0``. (:issue:`7075`)
* Implement a generic file filtering decision function for use in hooks,
  based on the source filename and optional inclusion and exclusion pattern
  list (:func:`PyInstaller.utils.hooks.include_or_exclude_file`).
  (:issue:`7040`)
* Rework the module exclusion mechanism. The excluded module entries,
  specified via ``excludedimports`` list in the hooks, are now used to
  suppress module imports from corresponding nodes *during modulegraph
  construction*, rather than to remove the nodes from the graph as a
  post-processing step. This should make the module exclusion more robust,
  but the main benefit is that we avoid running (potentially many and
  potentially costly) hooks for modules that would end up excluded anyway.
  (:issue:`7066`)


Bugfix
~~~~~~

* (Windows) Attempt to extend DLL search paths with directories found in
  the `PATH` environment variable and by tracking calls to the
  `os.add_dll_directory` function during import of the packages in
  the isolated sub-process that performs the binary dependency scanning.
  (:issue:`6924`)
* (Windows) Ensure that ANGLE DLLs (``libEGL.dll`` and ``libGLESv2.dll``)
  are collected when using Anaconda-installed ``PyQt5`` and ``Qt5``.
  (:issue:`7029`)
* Fix :class:`AssertionError` during build when analysing a ``.pyc`` file
  containing more that 255 variable names followed by an import statement all
  in
  the same namespace. (:issue:`7055`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (Windows) PyInstaller now attempts to preserve parent directory structure
  of DLLs that are collected from python packages (e.g., bundled with
  packages in PyPI wheels) instead of collecting them to the top-level
  application directory. This behavior might be incompatible with 3rd
  party hooks that assume the old behavior, and may result in duplication
  of DLL files or missing DLLs in hook-provided runtime search paths.
  (:issue:`7028`)


Hooks
~~~~~

* Implement new ``gstreamer`` hook configuration group with
  ``include_plugins`` and ``exclude_plugins`` options that enable control
  over GStreamer plugins collected by the ``gi.repository.Gst`` hook.
  (:issue:`7040`)
* Provide hooks for additional ``gstreamer`` modules provided via
  GObject introspection (``gi``) bindings: ``gi.repository.GstAllocators``,
  ``gi.repository.GstApp``, ``gi.repository.GstBadAudio``,
  ``gi.repository.GstCheck``,
  ``gi.repository.GstCodecs``, ``gi.repository.GstController``,
  ``gi.repository.GstGL``,
  ``gi.repository.GstGLEGL``, ``gi.repository.GstGLWayland``,
  ``gi.repository.GstGLX11``,
  ``gi.repository.GstInsertBin``, ``gi.repository.GstMpegts``,
  ``gi.repository.GstNet``,
  ``gi.repository.GstPlay``, ``gi.repository.GstPlayer``,
  ``gi.repository.GstRtp``,
  ``gi.repository.GstRtsp``, ``gi.repository.GstRtspServer``,
  ``gi.repository.GstSdp``,
  ``gi.repository.GstTranscoder``, ``gi.repository.GstVulkan``,
  ``gi.repository.GstVulkanWayland``,
  ``gi.repository.GstVulkanXCB``, and ``gi.repository.GstWebRTC``.
  (:issue:`7074`)


5.3 (2022-07-30)
-----------------

Features
~~~~~~~~

* (Windows) Implement handling of console control signals in the ``onefile``
  bootloader parent process. The implemented handler suppresses the
  ``CTRL_C_EVENT`` and ``CTRL_BREAK_EVENT`` to let the child process
  deal with them as they see it fit. In the case of ``CTRL_CLOSE_EVENT``,
  ``CTRL_LOGOFF_EVENT``, or ``CTRL_SHUTDOWN_EVENT``, the handler attempts
  to delay the termination of the parent process in order to buy time for
  the child process to exit and for the main thread of the parent process
  to clean up the temporary directory before exiting itself. This should
  prevent the temporary directory of a ``onefile`` frozen application
  being left behind when the user closes the console window. (:issue:`6591`)
* Implement a mechanism for controlling the collection mode of modules and
  packages, with granularity ranging from top-level packages to individual
  sub-modules. Therefore, the hooks can now specify whether the hooked
  package should be collected as byte-compiled .pyc modules into embedded
  PYZ archive (the default behavior), or as source .py files collected as
  external data files (without corresponding modules in the PYZ archive).
  (:issue:`6945`)


Bugfix
~~~~~~

* (non-Windows) Avoid generating debug messages in POSIX signal handlers,
  as the functions involved are generally not signal-safe. Should also
  fix the endless spam of ``SIGPIPE`` that ocurrs under certain conditions
  when shutting down the frozen application on linux. (:issue:`5270`)
* (non-Windows) If the child process of a ``onefile`` frozen application
  is terminated by a signal, delay re-raising of the signal in the parent
  process until after the clean up has been performed. This prevents
  ``onefile`` frozen applications from leaving behind their unpacked
  temporary directories when either the parent or the child process is
  sent the ``SIGTERM`` signal. (:issue:`2379`)
* When building with ``noarchive=True`` (e.g., ``--debug noarchive`` or
  ``--debug all``), PyInstaller no longer pollutes user-writable source
  locations with its ``.pyc`` or ``.pyo`` files written next to the
  corresponding source files. (:issue:`6591`)
* When building with ``noarchive=True`` (e.g., ``--debug noarchive`` or
  ``--debug all``), the source paths are now stripped from the collected
  .pyc modules, same as if PYZ archive was used. (:issue:`6591`)


Hooks
~~~~~

* Add PyGObject hook for ``gi.repository.freetype2``. Remove warning for
  hidden import not found for gi._gobject with PyGObject 3.25.1+.
  (:issue:`6951`)
* Remove ``pkg_resources`` hidden imports that aren't available including
  ``py2_warn``, ``markers``, and ``_vendor.pyparsing.diagram``. (:issue:`6952`)


Documentation
~~~~~~~~~~~~~

* Document the signal handling behavior Windows and various quirks related
  to the frozen application shutdown via the Task Manager. (:issue:`6935`)


5.2 (2022-07-08)
-----------------

Features
~~~~~~~~

* Detect if an icon file (``.ico`` or ``.icns``) is of another image type but
  has been mislabelled as a native icon type via its file suffix then either
  normalise to a genuinely native image type if ``pillow`` is installed or raise
  an error. (:issue:`6870`)
* Exit gracefully with an explanatory :class:`SystemExit` if the user moves or
  deletes the application whilst it's still running. Note that this is only
  detected on trying to load a module which has not already been loaded.
  (:issue:`6856`)
* Implement new standard hook variable, called
  ``warn_on_missing_hiddenimports``. This optional boolean flag allows a hook to
  opt out from warnings generated by missing hidden imports originating from
  that hook. (:issue:`6914`)


Bugfix
~~~~~~

* (Linux) Fix potential mismatch between the collected Python shared library
  name and the name expected by the bootloader when using Anaconda environment.
  The mismatch would occur on some attempts to freeze a program that uses an
  extension that is also linked against the python shared library.
  (:issue:`6831`)
* (Linux) Fix the missing ``gi.repository`` error in an application frozen on
  RHEL/Fedora linux with GObject introspection installed from the distribution's
  RPM package. (:issue:`6780`)
* (macOS) The ``QtWebEngine`` hook now makes ``QtOpenGL`` and ``QtDBus``
  available to the renderer process with framework installs of Qt 6.
  (:issue:`6892`)
* (Windows) Optimize EXE PE headers fix-up process in an attempt to reduce the
  processing time and the memory footprint with large onefile builds.
  (:issue:`6874`)
* Add a try/except guard around :func:`ctypes.util.find_library` to protect
  against `CPython bug #93094 <https://github.com/python/cpython/issues/93094>`_
  which leads to a :class:`FileNotFoundError`. (:issue:`6864`)
* Fix regression in PyInstaller v5 where an import of a non-existent GObject
  introspection (`gi`) module (for example, an optional dependency) in the
  program causes a build-time error and aborts the build process.
  (:issue:`6897`)
* If passed a name of an importable module instead of a package, the
  :func:`PyInstaller.utils.hooks.collect_submodules` function now returns
  a list containing the module's name, same as it would for a package without
  submodules. (:issue:`6850`)
* Prevent :func:`PyInstaller.utils.hooks.collect_submodules` from recursing into
  sub-packages that are excluded by the function passed via the ``filter``
  argument. (:issue:`6846`)
* The :func:`PyInstaller.utils.hooks.collect_submodules` function now excludes
  un-importable subpackages from the returned modules list. (:issue:`6850`)


Hooks
~~~~~

* (macOS) Disable ``QtWebEngine`` sandboxing for Qt6 in the corresponding
  ``PySide6`` and ``PyQt6`` run-time hooks as a work-around for the
  ``QtWebEngineProcess`` helper process crashing. This is required as of Qt
  6.3.1 due to the way PyInstaller collects Qt libraries, but is applied
  regardless of the used Qt6 version. If you are using an older version of Qt6
  and would like to keep the sandboxing, reset the
  ``QTWEBENGINE_DISABLE_SANDBOX`` environment variable at the start of your
  program, before importing Qt packages. (:issue:`6903`)
* Add support for GTK4 by adding dependencies and updating ``gi.repository.Gtk``
  and ``gi.repository.Gdk`` to work with ``module-versions`` in hooksconfig for
  ``gi``. (:issue:`6834`)
* Refactor the GObject introspection (``gi``) hooks so that the processing is
  performed only in hook loading stage or in the ``hook()`` function, but not in
  the mixture of two. (:issue:`6901`)
* Update the GObject introspection (``gi``) hooks to use newly-introduced
  ``GiModuleInfo`` object to:

   - Check for module availability.
   - Perform typelib data collection; equivalent of old ``get_gi_typelibs``
     function call.
   - Obtain associated shared library path, equivalent of old ``get_gi_libdir``
     function call.

  The ``get_gi_typelibs`` and ``get_gi_libdir`` functions now internally
  use ``GiModuleInfo`` to provide backwards-compatibility for external
  users. (:issue:`6901`)


5.1 (2022-05-17)
-----------------

Bugfix
~~~~~~

* (Windows) Fix the regression causing the (relative) spec path ending up
  prepended to relative icon path twice, resulting in icon not being found.
  (:issue:`6788`)
* Prevent collection of an entire Python site when using
  :func:`~PyInstaller.utils.hooks.collect_data_files` or
  :func:`~PyInstaller.utils.hooks.collect_dynamic_libs` for single-file modules
  (:issue:`6789`)
* Prevent the hook utility functions, such as
  :func:`~PyInstaller.utils.hooks.collect_submodules`,
  :func:`~PyInstaller.utils.hooks.collect_data_files`, and
  :func:`~PyInstaller.utils.hooks.collect_dynamic_libs`, from failing to
  identify a package when its PEP451-compliant loader does not implement
  the optional ``is_package`` method. (:issue:`6790`)
* The :func:`~PyInstaller.utils.hooks.get_package_paths` function now
  supports PEP420 namespace packages - although for backwards-compatibility
  reasons, it returns only the first path when multiple paths are
  present. (:issue:`6790`)
* The hook utility functions
  :func:`~PyInstaller.utils.hooks.collect_submodules`,
  :func:`~PyInstaller.utils.hooks.collect_data_files`, and
  :func:`~PyInstaller.utils.hooks.collect_dynamic_libs`) now support
  collection from PEP420 namespace packages. (:issue:`6790`)
* The user-provided spec file path and paths provided via :option:`--workpath`
  and :option:`--distpath` are now resolved to absolute full paths before being
  passed to PyInstaller's internals. (:issue:`6788`)


Hooks
~~~~~

* Exclude ``doctest`` in the ``pickle`` hook. Update ``PySide2``, ``PySide6``,
  ``PyQt5``, and ``PyQt6`` hooks with hidden imports that were previously
  pulled in by ``doctest`` (that was in turn pulled in by ``pickle``).
  (:issue:`6797`)


Bootloader
~~~~~~~~~~

* (Windows) Update the bundled ``zlib`` sources to v1.2.12. (:issue:`6804`)


Bootloader build
~~~~~~~~~~~~~~~~

* Building on Windows with MSVC no longer falls to bits if the PyInstaller repo
  is
  stored in a directory with a long path. (:issue:`6806`)


5.0.1 (2022-04-25)
------------------

Bugfix
~~~~~~

* (Linux) Have ``glib`` runtime hook prepend the frozen application's data
  dir to the ``XDG_DATA_DIRS`` environment variable instead of completely
  overwriting it. This should fix the case when ``xdg-open`` is used to
  launch a system-installed application (for example, opening an URL in a
  web browser via the ``webbrowser`` module) and no registered applications
  being found. (:issue:`3668`)
* Prevent unactionable errors raised by UPX from terminating the build.
  (:issue:`6757`)
* Restore the pre PyInstaller 5.0 behavior of resolving relative paths to icons
  as
  relative to the spec file rather than the current working directory.
  (:issue:`6759`)
* (Windows) Update system DLL inclusion list to allow collection of DLLs from
  Visual Studio 2012 (VC11) runtime and Visual Studio 2013 (VC12) runtime,
  as well as the latest version of Visual Studio 2015/2017/2019/2022 (VC14)
  runtime (14.3). (:issue:`6778`)


Hooks
~~~~~

* Refactor ``QtWebEngine`` hooks to support both pure Widget-based and
  pure QML/Quick-based applications. (:issue:`6753`)
* Update PySide6 and PyQt6 hooks for compatibility with Qt 6.3. ``QtWebEngine``
  on Windows and Linux does not provide the ``qt.conf`` file for the helper
  executable anymore, so we generate our own version of the file in order for
  ``QtWebengine`` -based frozen applications to work. (:issue:`6769`)


5.0 (2022-04-15)
----------------

Features
~~~~~~~~

* (macOS) App bundles built in ``onedir`` mode can now opt-in for :ref:`argv
  emulation <macos event forwarding and argv emulation>` so that file paths
  passed from the UI (`Open with...`) are reflected in :data:`sys.argv`.
  (:issue:`5908`)
* (macOS) App bundles built in ``onedir`` mode can now opt-in for :ref:`argv
  emulation <macos event forwarding and argv emulation>` so that file paths
  received in initial drag & drop event are reflected in :data:`sys.argv`.
  (:issue:`5436`)
* (macOS) The :ref:`argv emulation <macos event forwarding and argv emulation>`
  functionality is now available as an optional feature for app bundles
  built in either ``onefile`` or ``onedir`` mode. (:issue:`6089`)
* (Windows) Embed the manifest into generated ``onedir`` executables by
  default, in order to avoid potential issues when user renames the executable
  (e.g., the manifest not being found anymore due to activation context
  caching when user renames the executable and attempts to run it before
  also renaming the manifest file). The old behavior of generating the
  external manifest file in ``onedir`` mode can be re-enabled using the
  ``--no-embed-manifest`` command-line switch, or via the
  ``embed_manifest=False`` argument to ``EXE()`` in the .spec file.
  (:issue:`6223`)
* (Wine) Prevent collection of Wine built-in DLLs (in either PE-converted or
  fake/placeholder form) when building a Windows frozen application under
  Wine. Display a warning for each excluded Wine built-in DLL. (:issue:`6149`)
* Add a :mod:`PyInstaller.isolated` submodule as a safer replacement to
  :func:`PyInstaller.utils.hooks.exec_statement`. (:issue:`6052`)
* Improve matching of UPX exclude patterns to include OS-default case
  sensitivity,
  the wildcard operator (``*``), and support for parent directories in the
  pattern.
  Enables use of patterns like ``"Qt*.dll"`` and ``"PySide2*.pyd"``.
  (:issue:`6161`)
* Make the error handing of :func:`~PyInstaller.utils.hooks.collect_submodules`
  configurable. (:issue:`6052`)


Bugfix
~~~~~~

* (macOS) Fix potential loss of Apple Events during ``onefile`` app bundle
  start-up, when the child process is not yet ready to receive events
  forwarded by the parent process. (:issue:`6089`)
* (Windows) Remove the attempt to load the manifest of a ``onefile``
  frozen executable via the activation context, which fails with *An
  attempt to set the process default activation context failed because
  the process default activation context was already set.* message that
  can be observed in debug builds. This approach has been invalid ever
  since :issue:`3746` implemented direct manifest embedding into the
  ``onefile`` executable. (:issue:`6203`)
* Fix an import leak when
  :func:`PyInstaller.utils.hooks.get_module_file_attribute`
  is called with a sub-module or a sub-package name. (:issue:`6169`)
* Fix an import leak when :func:`PyInstaller.utils.hooks.is_package`
  is called with a sub-module or a sub-package name. (:issue:`6169`)
* Fix import errors when calling ``get_gi_libdir()`` during packaging of GTK
  apps.
  Enable CI tests of GTK by adding PyGObject dependencies for the Ubuntu
  builds. (:issue:`6300`)
* Issue an error report if a `.spec` file will not be generated, but
  command-line options specific to that functionality are given.
  (:issue:`6660`)
* Prevent ``onefile`` cleanup from recursing into symlinked directories and
  just remove the link instead. (:issue:`6074`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (macOS) App bundles built in ``onefile`` mode do not perform
  :ref:`argv emulation <macos event forwarding and argv emulation>` by
  default anymore. The functionality of converting initial open document/URL
  events into ``sys.argv`` entries must now be explicitly opted-in,
  via ``argv_emulation=True`` argument to ``EXE()`` in the .spec file
  or via :option:`--argv-emulation` command-line flag. (:issue:`6089`)
* (Windows) By default, manifest is now embedded into the executable in
  ``onedir`` mode. The old behavior of generating the external manifest
  file can be re-enabled using the ``--no-embed-manifest``
  command-line switch, or via the ``embed_manifest=False`` argument to
  ``EXE()`` in the .spec file. (:issue:`6223`)
* Issue an error report if a `.spec` file will not be generated, but
  command-line options specific to that functionality are given.
  (:issue:`6660`)
* The :func:`PyInstaller.utils.hooks.get_module_attribute` function now
  returns the actual attribute value instead of its string representation.
  The external users (e.g., 3rd party hooks) of this function must adjust
  their handling of the return value accordingly. (:issue:`6169`)
* The ``matplotlib.backends`` hook no longer collects all available
  ``matplotlib`` backends, but rather tries to auto-detect the used
  backend(s) by default. The old behavior can be re-enabled via the
  :ref:`hook configuration option <matplotlib hook options>`. (:issue:`6024`)


Hooks
~~~~~

* Rework the ``matplotlib.backends`` hook to attempt performing
  auto-detection of the used backend(s) instead of collecting all
  available backends. Implement :ref:`hook configuration option
  <matplotlib hook options>` that allows users to switch between
  this new behavior and the old behavior of collecting all backends,
  or to manually specify the backend(s) to be collected. (:issue:`6024`)


Bootloader
~~~~~~~~~~

* Change the behaviour of the ``--no-universal2`` flag so that it now assumes
  the
  target architecture of the compiler (which may be overridden via the ``CC``
  environment variable to facilitate cross compiling). (:issue:`6096`)
* Refactor Apple Events handling code and move it into a separate source file.
  (:issue:`6089`)


Documentation
~~~~~~~~~~~~~

* Add a :ref:`new section <macos event forwarding and argv emulation>`
  describing Apple Event forwarding behavior on macOS and the optional
  `argv emulation` for macOS app bundles, along with its caveats.
  (:issue:`6089`)
* Update documentation on using ``UPX``. (:issue:`6161`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Drop support for Python 3.6. (:issue:`6475`)


Bootloader build
~~~~~~~~~~~~~~~~

* (Windows) Enable `Control Flow Guard
  <https://docs.microsoft.com/en-us/windows/win32/secbp/control-flow-guard>`_
  for the Windows bootloader. (:issue:`6136`)


4.10 (2022-03-05)
-----------------

Features
~~~~~~~~

* (Wine) Prevent collection of Wine built-in DLLs (in either PE-converted or
  fake/placeholder form) when building a Windows frozen application under
  Wine. Display a warning for each excluded Wine built-in DLL. (:issue:`6622`)


Bugfix
~~~~~~

* (Linux) Remove the timeout on ``objcopy`` operations to prevent wrongful
  abortions when processing large executables on slow disks. (:issue:`6647`)
* (macOS) Limit the strict architecture validation for collected binaries to
  extension modules only. Fixes architecture validation errors when a
  ``universal2`` package has its multi-arch extension modules' arch slices
  linked against distinct single-arch thin shared libraries, as is the
  case with ``scipy`` 1.8.0 macOS ``universal2`` wheel. (:issue:`6587`)
* (macOS) Remove the 60 seconds timeout for each ``codesign`` and ``lipo``
  operation which caused build abortion when
  processing huge binaries. (:issue:`6644`)
* (Windows) Use a made up (not ``.exe``) suffix for intermediate executable
  files during the build process to prevent
  antiviruses from attempting to scan the file whilst PyInstaller is still
  working on it leading to a
  :class:`PermissionError` at build time. (:issue:`6467`)
* Fix an attempt to collect a non-existent ``.pyc`` file when the corresponding
  source ``.py`` file has ``st_mtime`` set to zero. (:issue:`6625`)


Hooks
~~~~~

* Add ``IPython`` to the list of excluded packages in the ``PIL`` hook in
  order to prevent automatic collection of ``IPython`` when it is not
  imported anywhere else. This in turn prevents whole ``matplotlib`` being
  automatically pulled in when using  ``PIL.Image``. (:issue:`6605`)


Bootloader
~~~~~~~~~~

* Fix detection of 32-bit ``arm`` platform when Thumb instruction set is
  enabled in the compiler. In this case, the ``ctx.env.DEST_CPU`` in
  ``waf`` build script is set to ``thumb`` instead of ``arm``. (:issue:`6532`)


4.9 (2022-02-03)
----------------

Bugfix
~~~~~~

* Add support for external paths when running ``pkgutil.iter_modules``.
  Add support for multiple search paths to ``pkgutil.iter_modules``.
  Correctly handle ``pkgutil.iter_modules`` with an empty list.
  (:issue:`6529`)
* Fix finding ``libpython3x.so`` when Python is installed with pyenv and the
  python executable is not linked against ``libpython3x.so``. (:issue:`6542`)
* Fix handling of symbolic links in the path matching part of the
  PyInstaller's ``pkgutil.iter_modules`` replacement/override. (:issue:`6537`)


Hooks
~~~~~

* Add hooks for ``PySide6.QtMultimedia`` and ``PyQt6.QtMultimedia``.
  (:issue:`6489`)
* Add hooks for ``QtMultimediaWidgets`` of all four supported Qt bindings
  (``PySide2``, ``PySide6``, ``PyQt5``, and ``PySide6``). (:issue:`6489`)
* Add support for ``setuptools 60.7.1`` and its vendoring  of ``jaraco.text``
  in ``pkg_resources``. Exit with an error message if ``setuptools 60.7.0``
  is encountered due to incompatibility with PyInstaller's loader logic.
  (:issue:`6564`)
* Collect the ``QtWaylandClient``-related plugins to enable Wayland support in
  the
  frozen applications using any of the four supported Qt bindings (``PySide2``,
  ``PyQt5``, ``PySide6``, and ``PyQt6``). (:issue:`6483`)
* Fix the issue with missing ``QtMultimediaWidgets`` module when using
  ``PySide2.QtMultimedia`` or ``PySide6.QtMultimedia`` in combination
  with PySide's ``true_property`` `feature
  <https://doc.qt.io/qtforpython/feature-why.html#the-true-property-feature>`_.
  (:issue:`6489`)


4.8 (2022-01-06)
----------------

Features
~~~~~~~~

* (Windows) Set the executable's build time in PE header to the current
  time. A custom timestamp can be specified via the ``SOURCE_DATE_EPOCH``
  environment variable to allow reproducible builds. (:issue:`6469`)
* Add strictly unofficial support for the `Termux
  <https://f-droid.org/en/packages/com.termux/>`_ platform. (:issue:`6484`)
* Replace the dual-process ``onedir`` mode on Linux and other Unix-like OSes
  with a single-process implementation. This makes ``onedir`` mode on these
  OSes comparable to Windows and macOS, where single-process ``onedir`` mode
  has already been used for a while. (:issue:`6407`)


Bugfix
~~~~~~

* (macOS) Fix regression in generation of ``universal2`` executables that
  caused the generated executable to fail ``codesign`` strict validation.
  (:issue:`6381`)
* (Windows) Fix ``onefile`` extraction behavior when the run-time temporary
  directory is set to a drive letter. The application's temporary directory
  is now created directly on the specified drive as opposed to the current
  directory on the specified drive. (:issue:`6051`)
* (Windows) Fix compatibility issues with python 3.9.8 from python.org, arising
  from the lack of embedded manifest in the ``python.exe`` executable.
  (:issue:`6367`)
* (Windows) Fix stack overflow in `pyarmor`-protected frozen applications,
  caused
  by the executable's stack being smaller than that of the python interpreter.
  (:issue:`6459`)
* (Windows) Fix the ``python3.dll`` shared library not being found and
  collected when using Python from MS App Store. (:issue:`6390`)
* Fix a bug that prevented traceback from uncaught exception to be
  retrieved and displayed in the windowed bootloader's error reporting
  facility (uncaught exception dialog on Windows, syslog on macOS).
  (:issue:`6426`)
* Fix a crash when a onefile build attempts to overwrite an existing onedir
  build
  on macOS or Linux (:issue:`6418`)
* Fix build errors when a linux shared library (.so) file is collected as
  a binary on macOS. (:issue:`6327`)
* Fix build errors when a Windows DLL/PYD file is collected as a binary on
  a non-Windows OS. (:issue:`6327`)
* Fix handling of encodings when reading the collected .py source files
  via ``FrozenImporter.get_source()``. (:issue:`6143`)
* Fix hook loader function not finding hooks if path has whitespaces.
  (Re-apply the fix that has been inadvertedly undone during the
  codebase reformatting.) (:issue:`6080`)
* Windows: Prevent invalid handle errors when an application compiled in
  :option:`--windowed` mode uses :mod:`subprocess`
  without explicitly setting **stdin**, **stdout** and **stderr** to either
  :data:`~subprocess.PIPE` or
  :data:`~subprocess.DEVNULL`. (:issue:`6364`)


Hooks
~~~~~

* (macOS) Add support for Anaconda-installed ``PyQtWebEngine``.
  (:issue:`6373`)
* Add hooks for ``PySide6.QtWebEngineWidgets`` and
  ``PyQt6.QtWebEngineWidgets``.
  The ``QtWebEngine`` support in PyInstaller requires ``Qt6`` v6.2.2 or later,
  so if an earlier version is encountered, we exit with an error instead of
  producing a defunct build. (:issue:`6387`)
* Avoid collecting the whole ``QtQml`` module and its dependencies in cases
  when it is not necessary (i.e., the application does not use ``QtQml`` or
  ``QtQuick`` modules). The unnecessary collection was triggered due to
  extension modules being linked against the ``libQt5Qml`` or ``libQt6Qml``
  shared library, and affected pure widget-based applications (``PySide2``
  and ``PySide6`` on Linux) and widget-based applications that use
  ``QtWebEngineWidgets`` (``PySide2``, ``PySide6``, ``PyQt5``, and ``PyQt6``
  on all OSes). (:issue:`6447`)
* Update ``numpy`` hook for compatibility with version 1.22; the hook
  cannot exclude ``distutils`` and ``numpy.distutils`` anymore, as they
  are required by ``numpy.testing``, which is used by some external
  packages, such as ``scipy``. (:issue:`6474`)


Bootloader
~~~~~~~~~~

* (Windows) Set the bootloader executable's stack size to 2 MB to match the
  stack size of the python interpreter executable. (:issue:`6459`)
* Implement single-process ``onedir`` mode for Linux and Unix-like OSes as a
  replacement for previously-used two-process implementation. The new mode
  uses ``exec()`` without ``fork()`` to restart the bootloader executable
  image within the same process after setting up the environment (i.e., the
  ``LD_LIBRARY_PATH`` and other environment variables). (:issue:`6407`)
* Lock the PKG sideload mode in the bootloader unless the executable has a
  special signature embedded. (:issue:`6470`)
* When user script terminates with an uncaught exception, ensure that the
  exception data obtained via ``PyErr_Fetch`` is normalized by also calling
  ``PyErr_NormalizeException``. Otherwise, trying to format the traceback
  via ``traceback.format_exception`` fails in some circumstances, and no
  traceback can be displayed in the windowed bootloader's error report.
  (:issue:`6426`)


Bootloader build
~~~~~~~~~~~~~~~~

* The bootloader can be force compiled during pip install by setting the
  environment variable ``PYINSTALLER_COMPILE_BOOTLOADER``. (:issue:`6384`)


4.7 (2021-11-10)
----------------

Bugfix
~~~~~~

* Fix a bug since v4.6 where certain Unix system directories were incorrectly
  assumed to exist and resulted in
  a :class:`FileNotFoundError`. (:issue:`6331`)


Hooks
~~~~~

* Update ``sphinx`` hook for compatibility with latest version (4.2.0).
  (:issue:`6330`)


Bootloader
~~~~~~~~~~

* (Windows) Explicitly set ``NTDDI_VERSION=0x06010000`` and
  ``_WIN32_WINNT=0x0601`` when compiling Windows bootloaders to request
  Windows 7 feature level for Windows headers. The windowed bootloader
  requires at least Windows Vista feature level, and some toolchains
  (e.g., mingw cross-compiler on linux) set too low level by default.
  (:issue:`6338`)
* (Windows) Remove the check for the unused ``windres`` utility when compiling
  with MinGW toolchain. (:issue:`6339`)
* Replace use of ``PyRun_SimpleString`` with ``PyRun_SimpleStringFlags``.
  (:issue:`6332`)


4.6 (2021-10-29)
-------------------------------

Features
~~~~~~~~

* Add support for Python 3.10. (:issue:`5693`)

* (Windows) Embed the manifest into generated ``onedir`` executables by
  default, in order to avoid potential issues when user renames the executable
  (e.g., the manifest not being found anymore due to activation context
  caching when user renames the executable and attempts to run it before
  also renaming the manifest file). The old behavior of generating the
  external manifest file in ``onedir`` mode can be re-enabled using the
  ``--no-embed-manifest`` command-line switch, or via the
  ``embed_manifest=False`` argument to ``EXE()`` in the .spec file.
  (:issue:`6248`)
* (Windows) Respect :pep:`239` encoding specifiers in Window's VSVersionInfo
  files. (:issue:`6259`)
* Implement basic resource reader for accessing on-filesystem resources (data
  files)
  via ``importlib.resources`` (python >= 3.9) or ``importlib_resources``
  (python <= 3.8). (:issue:`5616`)
* Ship precompiled wheels for musl-based Linux distributions (such as Alpine or
  OpenWRT) on ``x86_64`` and ``aarch64``. (:issue:`6245`)


Bugfix
~~~~~~

* (macOS) Ensure that executable pre-processing and post-processing steps
  (target arch selection, SDK version adjustment, (re)signing) are applied in
  the stand-alone PKG mode. (:issue:`6251`)
* (macOS) Robustify the macOS assembly pipeline to work around the issues with
  the ``codesign`` utility on macOS 10.13 High Sierra. (:issue:`6167`)
* (Windows) Fix collection of ``sysconfig`` platform-specific data module when
  using MSYS2/MINGW python. (:issue:`6118`)
* (Windows) Fix displayed script name and exception message in the
  unhandled exception dialog (windowed mode) when bootloader is compiled
  using the ``MinGW-w64`` toolchain. (:issue:`6199`)
* (Windows) Fix issues in ``onedir`` frozen applications when the bootloader
  is compiled using a toolchain that forcibly embeds a default manifest
  (e.g., the ``MinGW-w64`` toolchain from ``msys2``). The issues range from
  manifest-related options (e.g., ``uac-admin``) not working to windowed frozen
  application not starting at all (with the ``The procedure entry point
  LoadIconMetric could not be located...`` error message). (:issue:`6196`)
* (Windows) Fix the declared length of strings in the optional embedded
  product version information resource structure. The declared lengths
  were twice too long, and resulted in trailing garbage characters when
  the version information was read using `ctypes` and winver API.
  (:issue:`6219`)
* (Windows) Remove the attempt to load the manifest of a ``onefile``
  frozen executable via the activation context, which fails with ``An
  attempt to set the process default activation context failed because
  the process default activation context was already set.`` message that
  can be observed in debug builds. This approach has been invalid ever
  since :issue:`3746` implemented direct manifest embedding into the
  ``onefile`` executable. (:issue:`6248`)
* (Windows) Suppress missing library warnings for ``api-ms-win-core-*`` DLLs.
  (:issue:`6201`)
* (Windows) Tolerate reading Windows VSVersionInfo files with unicode byte
  order
  marks. (:issue:`6259`)
* Fix ``sys.executable`` pointing to the external package file instead of
  the executable when in package side-load mode (``pkg_append=False``).
  (:issue:`6202`)
* Fix a runaway glob which caused ``ctypes.util.find_library("libfoo")`` to
  non-deterministically pick any library
  matching ``libfoo*`` to bundle instead of ``libfoo.so``. (:issue:`6245`)
* Fix compatibility with with MIPS and loongarch64 architectures.
  (:issue:`6306`)
* Fix the ``FrozenImporter.get_source()`` to correctly handle the packages'
  ``__init__.py`` source  files. This in turn fixes missing-source-file
  errors for packages that use ``pytorch`` JIT when the source .py files
  are collected and available (for example, ``kornia``). (:issue:`6237`)
* Fix the location of the generated stand-alone pkg file when using the
  side-load mode (``pkg_append=False``) in combination with ``onefile`` mode.
  The package file is now placed next to the executable instead of next to
  the .spec file. (:issue:`6202`)
* When generating spec files, avoid hard-coding the spec file's location as the
  ``pathex`` argument to the ``Analysis``. (:issue:`6254`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (Windows) By default, manifest is now embedded into the executable in
  ``onedir`` mode. The old behavior of generating the external manifest
  file can be re-enabled using the ``--no-embed-manifest``
  command-line switch, or via the ``embed_manifest=False`` argument to
  ``EXE()`` in the .spec file. (:issue:`6248`)


Hooks
~~~~~

* (macOS) Fix compatibility with Anaconda ``PyQt5`` package. (:issue:`6181`)
* Add a hook for ``pandas.plotting`` to restore compatibility with ``pandas``
  1.3.0
  and later. (:issue:`5994`)
* Add a hook for ``QtOpenGLWidgets`` for ``PyQt6`` and ``PySide6`` to collect
  the new ``QtOpenGLWidgets`` module introduced in Qt6 (:issue:`6310`)
* Add hooks for ``QtPositioning`` and ``QtLocation`` modules of the Qt5-based
  packages (``PySide2`` and ``PyQt5``) to ensure that corresponding plugins
  are collected. (:issue:`6250`)
* Fix compatibility with ``PyQt5`` 5.9.2 from conda's  main channel.
  (:issue:`6114`)
* Prevent potential error in hooks for Qt-based packages that could be
  triggered
  by a partial ``PyQt6`` installation. (:issue:`6141`)
* Update ``QtNetwork`` hook for ``PyQt6`` and ``PySide6``  to collect the
  new ``tls`` plugins that were introduced in Qt 6.2. (:issue:`6276`)
* Update the ``gi.repository.GtkSource`` hook to accept a module-versions
  hooksconfig dict in order to allow the hook to be used with GtkSource
  versions
  greater than 3.0. (:issue:`6267`)


Bootloader
~~~~~~~~~~

* (Windows) Suppress two ``snprintf`` truncation warnings that prevented
  bootloader from building with ``winlibs MinGW-w64`` toolchain.
  (:issue:`6196`)
* Update the Linux bootloader cross compiler Dockerfile to allow using `the
  official PyPA base images
  <https://quay.io/organization/pypa/>`_ in place of the dockcross ones.
  (:issue:`6245`)


4.5.1 (2021-08-06)
------------------

Bugfix
~~~~~~

* Fix hook loader function not finding hooks if path has whitespaces.
  (:issue:`6080`)


4.5 (2021-08-01)
----------------

Features
~~~~~~~~

* (POSIX) Add ``exclude_system_libraries`` function to the Analysis class
  for .spec files,
  to exclude most or all non-Python system libraries from the bundle.
  Documented in new :ref:`POSIX Specific Options` section. (:issue:`6022`)


Bugfix
~~~~~~

* (Cygwin) Add ``_MEIPASS`` to DLL search path to fix loading of python shared
  library in onefile builds made in cygwin environment and executed outside of
  it. (:issue:`6000`)
* (Linux) Display missing library warnings for "not found" lines in ``ldd``
  output (i.e., ``libsomething.so => not found``) instead of quietly
  ignoring them. (:issue:`6015`)
* (Linux) Fix spurious missing library warning when ``libc.so`` points to
  ``ldd``. (:issue:`6015`)
* (macOS) Fix python shared library detection for non-framework python builds
  when the library  path cannot be inferred from imports of the ``python``
  executable. (:issue:`6021`)
* (macOS) Fix the crashes in ``onedir`` bundles of ``tkinter``-based
  applications
  created using Homebrew python 3.9 and Tcl/Tk 8.6.11. (:issue:`6043`)
* (macOS) When fixing executable for codesigning, update the value of
  ``vmsize`` field in the ``__LINKEDIT`` segment. (:issue:`6039`)
* Downgrade messages about missing dynamic link libraries from ERROR to
  WARNING. (:issue:`6015`)
* Fix a bytecode parsing bug which caused tuple index errors whilst scanning
  modules which use :mod:`ctypes`. (:issue:`6007`)
* Fix an error when rhtooks for ``pkgutil`` and ``pkg_resources`` are used
  together. (:issue:`6018`)
* Fix architecture detection on Apple M1 (:issue:`6029`)
* Fix crash in windowed bootloader when the traceback for unhandled exception
  cannot be retrieved. (:issue:`6070`)
* Improve handling of errors when loading hook entry-points. (:issue:`6028`)
* Suppress missing library warning for ``shiboken2`` (``PySide2``) and
  ``shiboken6`` (``PySide6``) shared library. (:issue:`6015`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* (macOS) Disable processing of Apple events for the purpose of argv emulation
  in ``onedir`` application bundles. This functionality was introduced in
  PyInstaller 4.4 by (:issue:`5920`) in response to feature requests
  (:issue:`5436`) and (:issue:`5908`), but was discovered to be breaking
  ``tkinter``-based ``onedir`` bundles made with Homebrew python 3.9 and
  Tcl/Tk 8.6.11 (:issue:`6043`). As such, until the cause is investigated
  and the issue addressed, this feature is reverted/disabled. (:issue:`6048`)


Hooks
~~~~~

* Add a hook for ``pandas.io.formats.style`` to deal with indirect import of
  ``jinja2`` and the missing template file. (:issue:`6010`)
* Simplify the ``PySide2.QWebEngineWidgets`` and ``PyQt5.QWebEngineWidgets`` by
  merging most of their code into a common helper function. (:issue:`6020`)


Documentation
~~~~~~~~~~~~~

* Add a page describing hook configuration mechanism and the currently
  implemented options. (:issue:`6025`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Isolate discovery of 3rd-party hook directories into a separate
  subprocess to avoid importing packages in the main process. (:issue:`6032`)


Bootloader build
~~~~~~~~~~~~~~~~

* Allow statically linking zlib on non-Windows specified via either a
  ``--static-zlib`` flag or a ``PYI_STATIC_ZLIB=1`` environment variable.
  (:issue:`6010`)


4.4 (2021-07-13)
----------------

Features
~~~~~~~~

* (macOS) Implement signing of .app bundle (ad-hoc or with actual signing
  identity, if provided). (:issue:`5581`)
* (macOS) Implement support for Apple Silicon M1 (``arm64``) platform
  and different targets for frozen applications (thin-binary ``x86_64``,
  thin-binary ``arm64``, and fat-binary ``universal2``), with build-time
  arch validation and ad-hoc resigning of all collected binaries.
  (:issue:`5581`)
* (macOS) In ``onedir`` ``windowed`` (.app bundle) mode, perform an
  interaction of Apple event processing to convert ``odoc`` and ``GURL``
  events to ``sys.argv`` before entering frozen python script. (:issue:`5920`)
* (macOS) In windowed (.app bundle) mode, always log unhandled exception
  information to ``syslog``, regardless of debug mode. (:issue:`5890`)
* (Windows) Add support for Python from Microsoft App Store. (:issue:`5816`)
* (Windows) Implement a custom dialog for displaying information about
  unhandled
  exception and its traceback when running in windowed/noconsole mode.
  (:issue:`5890`)
* Add **recursive** option to :func:`PyInstaller.utils.hooks.copy_metadata()`.
  (:issue:`5830`)
* Add ``--codesign-identity``  command-line switch to perform code-signing
  with actual signing identity instead of ad-hoc signing (macOS only).
  (:issue:`5581`)
* Add ``--osx-entitlements-file`` command-line switch that specifies optional
  entitlements file to be used during code signing of collected binaries
  (macOS only). (:issue:`5581`)
* Add ``--target-arch`` command-line switch to select target architecture
  for frozen application (macOS only). (:issue:`5581`)
* Add a splash screen that displays a background image and text:
  The splash screen can be controlled from within Python using the
  ``pyi_splash`` module.
  A splash screen can be added using the ``--splash IMAGE_FILE`` option.
  If optional text is enabled, the splash screen will show the progress of
  unpacking in
  onefile mode.
  This feature is supported only on Windows and Linux.
  A huge thanks to `@Chrisg2000 <https://github.com/Chrisg2000>`_ for
  programming this feature. (:issue:`4354`, :issue:`4887`)
* Add hooks for ``PyQt6``. (:issue:`5865`)
* Add hooks for ``PySide6``. (:issue:`5865`)
* Add option to opt-out from reporting full traceback for unhandled exceptions
  in windowed mode (Windows and macOS only), via
  ``--disable-windowed-traceback``
  PyInstaller CLI switch and the corresponding ``disable_windowed_traceback``
  boolean argument to ``EXE()`` in spec file. (:issue:`5890`)
* Allow specify which icon set, themes and locales
  to pack with Gtk applications.
  Pass a keyword arg ``hooksconfig`` to
  Analysis.

  .. code-block:: python

      a = Analysis(["my-gtk-app.py"],
                   ...,
                   hooksconfig={
                       "gi": {
                           "icons": ["Adwaita"],
                           "themes": ["Adwaita"],
                           "languages": ["en_GB", "zh_CN"]
                       }
                   },
                   ...)

  (:issue:`5853`)
* Automatically exclude Qt plugins from UPX processing. (:issue:`4178`)
* Collect distribution metadata automatically.
  This works by scanning collected Python files for uses of:

  * ``pkg_resources.get_distribution()``
  * ``pkg_resources.require()``
  * ``importlib.metadata.distribution()``
  * ``importlib.metadata.metadata()``
  * ``importlib.metadata.files()``
  * ``importlib.metadata.version()``

  In all cases, the metadata will only be collected if the distribution name is
  given as a plain string literal. Anything more complex will still require a
  hook containing :func:`PyInstaller.utils.hooks.copy_metadata`.
  (:issue:`5830`)
* Implement support for :func:`pkgutil.iter_modules`. (:issue:`1905`)
* Windows: Provide a meaningful error message if given an icon in an
  unsupported
  Image format. (:issue:`5755`)


Bugfix
~~~~~~

* (macOS) App bundles built in ``onedir`` mode now filter out ``-psnxxx``
  command-line argument from ``sys.argv``, to keep behavior consistent
  with bundles built in ``onefile`` mode. (:issue:`5920`)
* (macOS) Ensure that the macOS SDK version reported by the frozen application
  corresponds to the minimum of the SDK version used to build the bootloader
  and the SDK version used to build the Python library. Having the application
  report more recent version than Python library and other bundled libraries
  may result in macOS attempting to enable additional features that are not
  available in the Python library, which may in turn cause inconsistent
  behavior
  and UI issues with ``tkinter``. (:issue:`5839`)
* (macOS) Remove spurious ``MacOS/`` prefix from ``CFBundleExecutable``
  property
  in the generated ``Info.plist`` when building an app bundle. (:issue:`4413`,
  :issue:`5442`)
* (macOS) The drag & drop file paths passed to app bundles built in
  ``onedir`` mode are now reflected in ``sys.argv``. (:issue:`5436`)
* (macOS) The file paths passed from the UI (`Open with...`) to app bundles
  built in ``onedir`` mode are now reflected in ``sys.argv``. (:issue:`5908`)
* (macOS) Work around the ``tkinter`` UI issues due to problems with
  dark mode activation: black ``Tk`` window with macOS Intel installers
  from ``python.org``, or white text on bright background with Anaconda
  python. (:issue:`5827`)
* (Windows) Enable collection of additional VC runtime DLLs (``msvcp140.dll``,
  ``msvcp140_1.dll``, ``msvcp140_2.dll``, and ``vcruntime140_1.dll``), to
  allow frozen applications to run on Windows systems that do not have
  `Visual Studio 2015/2017/2019 Redistributable` installed. (:issue:`5770`)
* Enable retrieval of code object for ``__main__`` module via its associated
  loader (i.e., ``FrozenImporter``). (:issue:`5897`)
* Fix :func:`inspect.getmodule` failing to resolve module from stack-frame
  obtained via :func:`inspect.stack`. (:issue:`5963`)
* Fix ``__main__`` module being recognized as built-in instead of module.
  (:issue:`5897`)
* Fix a bug in :ref:`ctypes dependency scanning <Ctypes Dependencies>` which
  caused references to be missed if the preceding code contains more than
  256 names or 256 literals. (:issue:`5830`)
* Fix collection of duplicated ``_struct`` and ``zlib`` extension modules
  with mangled filenames. (:issue:`5851`)
* Fix python library lookup when building with RH SCL python 3.8 or later.
  (:issue:`5749`)
* Prevent :func:`PyInstaller.utils.hooks.copy_metadata` from renaming
  ``[...].dist-info`` metadata folders to ``[...].egg-info`` which breaks usage
  of ``pkg_resources.requires()`` with *extras*. (:issue:`5774`)
* Prevent a bootloader executable without an embedded CArchive from being
  misidentified as having one, which leads to undefined behavior in frozen
  applications with side-loaded CArchive packages. (:issue:`5762`)
* Prevent the use of ``sys`` or ``os`` as variables in the global namespace
  in frozen script from affecting the ``ctypes`` hooks thar are installed
  during bootstrap. (:issue:`5797`)
* Windows: Fix EXE being rebuilt when there are no changes. (:issue:`5921`)


Hooks
~~~~~

* * Add ``PostGraphAPI.analysis`` attribute.
    Hooks can access the ``Analysis`` object
    through the ``hook()`` function.

  * Hooks may access a ``Analysis.hooksconfig`` attribute
    assigned on ``Analysis`` construction.

    A helper function :func:`~PyInstaller.utils.hooks.get_hook_config`
    was defined in ``utils.hooks`` to get the config. (:issue:`5853`)
* Add support for ``PyQt5`` 5.15.4. (:issue:`5631`)
* Do not exclude ``setuptools.py27compat`` and ``setuptools.py33compat``
  as they are required by other ``setuptools`` modules. (:issue:`5979`)
* Switch the library search order in ``ctypes`` hooks: first check whether
  the given name exists as-is, before trying to search for its basename in
  ``sys._MEIPASS`` (instead of the other way around). (:issue:`5907`)


Bootloader
~~~~~~~~~~

* (macOS) Build bootloader as ``universal2`` binary by default (can
  be disabled by passing ``--no-universal2`` to waf). (:issue:`5581`)
* Add Tcl/Tk based Splash screen, which is controlled from
  within Python. The necessary module to create the Splash
  screen in PyInstaller is under :mod:`Splash` available.
  A huge thanks to `@Chrisg2000 <https://github.com/Chrisg2000>`_ for
  programming this feature. (:issue:`4887`)
* Provide a Dockerfile to build Linux bootloaders for different architectures.
  (:issue:`5995`)


Documentation
~~~~~~~~~~~~~

* Document the new macOS multi-arch support and code-signing behavior
  in corresponding sub-sections of ``Notes about specific Features``.
  (:issue:`5581`)


Bootloader build
~~~~~~~~~~~~~~~~

* Update ``clang`` in ``linux64`` Vagrant VM to ``clang-11`` from
  ``apt.llvm.org`` so it can build ``universal2`` macOS bootloader.
  (:issue:`5581`)
* Update ``crossosx`` Vagrant VM to build the toolchain from ``Command Line
  Tools for Xcode`` instead of full ``Xcode package``. (:issue:`5581`)


4.3 (2021-04-16)
----------------

Features
~~~~~~~~

* Provide basic implementation for ``FrozenImporter.get_source()`` that
  allows reading source from ``.py`` files that are collected by hooks as
  data files. (:issue:`5697`)
* Raise the maximum allowed size of ``CArchive`` (and consequently ``onefile``
  executables) from 2 GiB to 4 GiB. (:issue:`3939`)
* The `unbuffered stdio` mode (the ``u`` option) now sets the
  ``Py_UnbufferedStdioFlag``
  flag to enable unbuffered stdio mode in Python library. (:issue:`1441`)
* Windows: Set EXE checksums. Reduces false-positive detection from antiviral
  software. (:issue:`5579`)
* Add new command-line options that map to collect functions from hookutils:
  ``--collect-submodules``, ``--collect-data``, ``--collect-binaries``,
  ``--collect-all``, and ``--copy-metadata``. (:issue:`5391`)
* Add new hook utility :func:`~PyInstaller.utils.hooks.collect_entry_point` for
  collecting plugins defined through setuptools entry points. (:issue:`5734`)


Bugfix
~~~~~~

* (macOS) Fix ``Bad CPU type in executable`` error in helper-spawned python
  processes when running under ``arm64``-only flavor of Python on Apple M1.
  (:issue:`5640`)
* (OSX) Suppress missing library error messages for system libraries as
  those are never collected by PyInstaller and starting with Big Sur,
  they are hidden by the OS. (:issue:`5107`)
* (Windows) Change default cache directory to ``LOCALAPPDATA``
  (from the original ``APPDATA``).
  This is to make sure that cached data
  doesn't get synced with the roaming profile.
  For this and future versions ``AppData\Roaming\pyinstaller``
  might be safely deleted. (:issue:`5537`)
* (Windows) Fix ``onefile`` builds not having manifest embedded when icon is
  disabled via ``--icon NONE``. (:issue:`5625`)
* (Windows) Fix the frozen program crashing immediately with
  ``Failed to execute script pyiboot01_bootstrap`` message when built in
  ``noconsole`` mode and with import logging enabled (either via
  ``--debug imports`` or ``--debug all`` command-line switch). (:issue:`4213`)
* ``CArchiveReader`` now performs full back-to-front file search for
  ``MAGIC``, allowing ``pyi-archive_viewer`` to open binaries with extra
  appended data after embedded package (e.g., digital signature).
  (:issue:`2372`)
* Fix ``MERGE()`` to properly set references to nested resources with their
  full shared-package-relative path instead of just basename. (:issue:`5606`)
* Fix ``onefile`` builds failing to extract files when the full target
  path exceeds 260 characters. (:issue:`5617`)
* Fix a crash in ``pyi-archive_viewer`` when quitting the application or
  moving up a level. (:issue:`5554`)
* Fix extraction of nested files in ``onefile`` builds created in MSYS
  environments. (:issue:`5569`)
* Fix installation issues stemming from unicode characters in
  file paths. (:issue:`5678`)
* Fix the build-time error under python 3.7 and earlier when ``ctypes``
  is manually added to ``hiddenimports``. (:issue:`3825`)
* Fix the return code if the frozen script fails due to unhandled exception.
  The return code 1 is used instead of -1, to keep the behavior consistent
  with that of the python interpreter. (:issue:`5480`)
* Linux: Fix binary dependency scanner to support `changes to ldconfig
  <https://sourceware.org/git/?p=glibc.git;a=commitdiff;h=dfb3f101c5ef23adf60d389058a2b33e23303d04>`_
  introduced in ``glibc`` 2.33. (:issue:`5540`)
* Prevent ``MERGE`` (multipackage) from creating self-references for
  duplicated TOC entries. (:issue:`5652`)
* PyInstaller-frozen onefile programs are now compatible with ``staticx``
  even if the bootloader is built as position-independent executable (PIE).
  (:issue:`5330`)
* Remove dependence on a `private function
  <https://github.com/matplotlib/matplotlib/commit/e1352c71f07aee7eab004b73dd9bda2a260ab31b>`_
  removed in ``matplotlib`` 3.4.0rc1. (:issue:`5568`)
* Strip absolute paths from ``.pyc`` modules collected into
  ``base_library.zip``
  to enable reproducible builds that are invariant to Python install location.
  (:issue:`5563`)
* (OSX) Fix issues with ``pycryptodomex`` on macOS. (:issue:`5583`)
* Allow compiled modules to be collected into ``base_library.zip``.
  (:issue:`5730`)
* Fix a build error triggered by scanning ``ctypes.CDLL('libc.so')`` on certain
  Linux C compiler combinations. (:issue:`5734`)
* Improve performance and reduce stack usage of module scanning.
  (:issue:`5698`)


Hooks
~~~~~

* Add support for Conda Forge's distribution of ``NumPy``. (:issue:`5168`)
* Add support for package content listing via ``pkg_resources``. The
  implementation enables querying/listing resources in a frozen package
  (both PYZ-embedded and on-filesystem, in that order of precedence) via
  ``pkg_resources.resource_exists()``, ``resource_isdir()``, and
  ``resource_listdir()``. (:issue:`5284`)
* Hooks: Import correct typelib for GtkosxApplication. (:issue:`5475`)
* Prevent ``matplotlib`` hook from collecting current working directory when it
  fails to determine the path to matplotlib's data directory. (:issue:`5629`)
* Update ``pandas`` hook for compatibility with version 1.2.0 and later.
  (:issue:`5630`)
* Update hook for ``distutils.sysconfig`` to be compatible with
  pyenv-virtualenv. (:issue:`5218`)
* Update hook for ``sqlalchemy`` to support version 1.4.0 and above.
  (:issue:`5679`)
* Update hook for ``sysconfig`` to be compatible with pyenv-virtualenv.
  (:issue:`5018`)


Bootloader
~~~~~~~~~~

* Implement full back-to-front file search for the embedded archive.
  (:issue:`5511`)
* Perform file extraction from the embedded archive in a streaming manner
  in order to limit memory footprint when archive contains large files.
  (:issue:`5551`)
* Set the ``__file__`` attribute in the ``__main__`` module (entry-point
  script) to the absolute file name inside the ``_MEIPASS``. (:issue:`5649`)
* Enable cross compiling for FreeBSD from Linux. (:issue:`5733`)


Documentation
~~~~~~~~~~~~~

* Doc: Add version spec file option for macOS Bundle. (:issue:`5476`)
* Update the ``Run-time Information`` section to reflect the changes in
  behavior of ``__file__`` inside the ``__main__`` module. (:issue:`5649`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Drop support for python 3.5; EOL since September 2020. (:issue:`5439`)
* Collect python extension modules that correspond to built-ins into
  ``lib-dynload`` sub-directory instead of directly into bundle's root
  directory. This prevents them from shadowing shared libraries with the
  same basename that are located in a package and loaded via ``ctypes`` or
  ``cffi``, and also declutters the bundle's root directory. (:issue:`5604`)

Breaking
~~~~~~~~

* No longer collect ``pyconfig.h`` and ``makefile`` for :mod:`sysconfig`. Instead
  of :func:`~sysconfig.get_config_h_filename` and
  :func:`~sysconfig.get_makefile_filename`, you should use
  :func:`~sysconfig.get_config_vars` which no longer depends on those files. (:issue:`5218`)
* The ``__file__`` attribute in the ``__main__`` module (entry-point
  script) is now set to the absolute file name inside the ``_MEIPASS``
  (as if script file existed there) instead of just script filename.
  This better matches the behavior of ``__file__`` in the unfrozen script,
  but might break the existing code that explicitly relies on the old
  frozen behavior. (:issue:`5649`)



4.2 (2021-01-13)
----------------

Features
~~~~~~~~

* Add hooks utilities to find binary dependencies of Anaconda distributions.
  (:issue:`5213`)
* (OSX) Automatically remove the signature from the collected copy of the
  ``Python`` shared library, using ``codesign --remove-signature``. This
  accommodates both ``onedir`` and ``onefile`` builds with recent python
  versions for macOS, where invalidated signature on PyInstaller-collected
  copy of the ``Python`` library prevents the latter from being loaded.
  (:issue:`5451`)
* (Windows) PyInstaller's console or windowed icon is now added at freeze-time
  and
  no longer built into the bootloader. Also, using ``--icon=NONE`` allows to
  not
  apply any icon, thereby making the OS to show some default icon.
  (:issue:`4700`)
* (Windows) Enable ``longPathAware`` option in built application's manifest in
  order to support long file paths on Windows 10 v.1607 and later.
  (:issue:`5424`)


Bugfix
~~~~~~

* Fix loading of plugin-type modules at run-time of the frozen application:
  If the plugin path is one character longer than sys._MEIPATH
  (e.g. "$PWD/p/plugin_1" and "$PWD/dist/main"),
  the plugin relative-imports a sub-module (of the plugin)
  and the frozen application contains a module of the same name,
  the frozen application module was imported. (:issue:`4141`, :issue:`4299`)
* Ensure that spec for frozen packages has ``submodule_search_locations`` set
  in order to fix compatibility  with ``importlib_resources`` 3.2.0 and later.
  (:issue:`5396`)
* Fix: No rebuild if "noarchive" build-option changes. (:issue:`5404`)
* (OSX) Fix the problem with ``Python`` shared library collected from
  recent python versions not being loaded due to invalidated signature.
  (:issue:`5062`, :issue:`5272`, :issue:`5434`)
* (Windows) PyInstaller's default icon is no longer built into the bootloader,
  but
  added at freeze-time. Thus, when specifying an icon, only that icon is
  contained in the executable and displayed for a shortcut. (:issue:`870`,
  :issue:`2995`)
* (Windows) Fix "toc is bad" error messages
  when passing a ``VSVersionInfo``
  as the ``version`` parameter to ``EXE()``
  in a ``.spec`` file. (:issue:`5445`)
* (Windows) Fix exception when trying to read a manifest from an exe or dll.
  (:issue:`5403`)
* (Windows) Fix the ``--runtime-tmpdir`` option by creating paths if they don't
  exist and expanding environment variables (e.g. ``%LOCALAPPDATA%``).
  (:issue:`3301`, :issue:`4579`, :issue:`4720`)


Hooks
~~~~~

* (GNU/Linux) Collect ``xcbglintegrations`` and ``egldeviceintegrations``
  plugins as part of ``Qt5Gui``. (:issue:`5349`)
* (macOS) Fix: Unable to code sign apps built with GTK (:issue:`5435`)
* (Windows) Add a hook for ``win32ctypes.core``. (:issue:`5250`)
* Add hook for ``scipy.spatial.transform.rotation`` to fix compatibility with
  SciPy 1.6.0. (:issue:`5456`)
* Add hook-gi.repository.GtkosxApplication to fix TypeError with Gtk macOS
  apps. (:issue:`5385`)
* Add hooks utilities to find binary dependencies of Anaconda distributions.
  (:issue:`5213`)
* Fix the ``Qt5`` library availability check in ``PyQt5`` and ``PySide2`` hooks
  to re-enable support for ``Qt5`` older than 5.8. (:issue:`5425`)
* Implement ``exec_statement_rc()`` and ``exec_script_rc()`` as exit-code
  returning counterparts of ``exec_statement()`` and ``exec_script()``.
  Implement ``can_import_module()`` helper for hooks that need to query module
  availability. (:issue:`5301`)
* Limit the impact of a failed sub-package import on the result of
  ``collect_submodules()`` to ensure that modules from all other sub-packages
  are collected. (:issue:`5426`)
* Removed obsolete ``pygame`` hook. (:issue:`5362`)
* Update ``keyring`` hook to collect metadata, which is required for backend
  discovery. (:issue:`5245`)


Bootloader
~~~~~~~~~~

* (GNU/Linux) Reintroduce executable resolution via ``readlink()`` on
  ``/proc/self/exe`` and preserve the process name using ``prctl()`` with
  ``PR_GET_NAME`` and ``PR_SET_NAME``. (:issue:`5232`)
* (Windows) Create temporary directories with user's SID instead of
  ``S-1-3-4``,
  to work around the lack of support for the latter in ``wine``.
  This enables ``onefile`` builds to run under ``wine`` again. (:issue:`5216`)
* (Windows) Fix a bug in path-handling code with paths exceeding ``PATH_MAX``,
  which is caused by use of ``_snprintf`` instead of ``snprintf`` when
  building with MSC. Requires Visual Studio 2015 or later.
  Clean up the MSC codepath to address other compiler warnings.
  (:issue:`5320`)
* (Windows) Fix building of bootloader's test suite under Windows with Visual
  Studio.
  This fixes build errors when ``cmocka`` is present in the build environment.
  (:issue:`5318`)
* (Windows) Fix compiler warnings produced by MinGW 10.2 in order to allow
  building the bootloader without having to suppress the warnings.
  (:issue:`5322`)
* (Windows) Fix ``windowed+debug`` bootloader variant not properly
  displaying the exception message and traceback information when the
  frozen script terminates due to uncaught exception. (:issue:`5446`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* (Windows) Avoid using UPX with DLLs that have control flow guard (CFG)
  enabled. (:issue:`5382`)
* Avoid using ``.pyo`` module file suffix (removed since PEP-488) in
  ``noarchive`` mode. (:issue:`5383`)
* Improve support for ``PEP-420`` namespace packages. (:issue:`5354`)
* Strip absolute paths from ``.pyc`` modules collected in the CArchive (PKG).
  This enables build reproducibility without having to match the location of
  the build environment. (:issue:`5380`)


4.1 (2020-11-18)
----------------

Features
~~~~~~~~

* Add support for Python 3.9. (:issue:`5289`)
* Add support for Python 3.8. (:issue:`4311`)


Bugfix
~~~~~~

* Fix endless recursion if a package's ``__init__`` module is an extension
  module. (:issue:`5157`)
* Remove duplicate logging messages (:issue:`5277`)
* Fix sw_64 architecture support (:issue:`5296`)
* (AIX) Include python-malloc labeled libraries in search for libpython.
  (:issue:`4210`)


Hooks
~~~~~

* Add ``exclude_datas``, ``include_datas``, and ``filter_submodules`` to
  ``collect_all()``. These arguments map to the ``excludes`` and ``includes``
  arguments of ``collect_data_files``, and to the `filter` argument of
  ``collect_submodules``. (:issue:`5113`)
* Add hook for difflib to not pull in doctests, which is only
  required when run as main program.
* Add hook for distutils.util to not pull in lib2to3 unittests, which will be
  rearly used in frozen packages.
* Add hook for heapq to not pull in doctests, which is only
  required when run as main program.
* Add hook for multiprocessing.util to not pull in python test-suite and thus
  e.g. tkinter.
* Add hook for numpy._pytesttester to not pull in pytest.
* Add hook for pickle to not pull in doctests and argpargs, which are only
  required when run as main program.
* Add hook for PIL.ImageFilter to not pull
  numpy, which is an optional component.
* Add hook for setuptools to not pull in numpy, which is only imported if
  installed, not mean to be a dependency
* Add hook for zope.interface to not pull in pytest unittests, which will be
  rearly used in frozen packages.
* Add hook-gi.repository.HarfBuzz to fix Typelib error with Gtk apps.
  (:issue:`5133`)
* Enable overriding Django settings path by `DJANGO_SETTINGS_MODULE`
  environment variable. (:issue:`5267`)
* Fix `collect_system_data_files` to scan the given input path instead of its
  parent.
  File paths returned by `collect_all_system_data` are now relative to the
  input path. (:issue:`5110`)
* Fix argument order in ``exec_script()`` and ``eval_script()``.
  (:issue:`5300`)
* Gevent hook does not unnecessarily bundle HTML documentation, __pycache__
  folders, tests nor generated .c and .h files (:issue:`4857`)
* gevent: Do not pull in test-suite (still to be refined)
* Modify hook for ``gevent`` to exclude test submodules. (:issue:`5201`)
* Prevent .pyo files from being collected by collect_data_files when
  include_py_files is False. (:issue:`5141`)
* Prevent output to ``stdout`` during module imports from ending up in the
  modules list collected by ``collect_submodules``. (:issue:`5244`)
* Remove runtime hook and fix regular hook for matplotlib's data to support
  ``matplotlib>=3.3.0``, fix deprecation warning on version 3.1<= & <3.3,
  and behave normally for versions <3.1. (:issue:`5006`)
* Remove support for deprecated PyQt4 and PySide (:issue:`5118`,
  :issue:`5126`)
* setuptools: Exclude outdated compat modules.
* Update ``sqlalchemy`` hook to support v1.3.19 and later,  by adding
  ``sqlalchemy.ext.baked`` as a hidden import (:issue:`5128`)
* Update ``tkinter`` hook to collect Tcl modules directory (``tcl8``) in
  addition to Tcl/Tk data directories. (:issue:`5175`)
* (GNU/Linux) {PyQt5,PySide2}.QtWebEngineWidgets: fix search for extra NSS
  libraries to prevent an error on systems where /lib64/nss/\*.so
  comes up empty. (:issue:`5149`)
* (OSX) Avoid collecting data from system Tcl/Tk framework in ``tkinter`` hook
  as we do not collect their shared libraries, either.
  Affects only python versions that still use the system Tcl/Tk 8.5.
  (:issue:`5217`)
* (OSX) Correctly locate the tcl/tk framework bundled with official
  python.org python builds from v.3.6.5 on. (:issue:`5013`)
* (OSX) Fix the QTWEBENGINEPROCESS_PATH set in PyQt5.QtWebEngineWidgets rthook.
  (:issue:`5183`)
* (OSX) PySide2.QtWebEngineWidgets: add QtQmlModels to included libraries.
  (:issue:`5150`)
* (Windows) Remove the obsolete python2.4-era ``_handle_broken_tcl_tk``
  work-around for old virtual environments from the ``tkinter`` hook.
  (:issue:`5222`)


Bootloader
~~~~~~~~~~

* Fix freeing memory allocated by Python using ``free()`` instead of
  ``PyMem_RawFree()``. (:issue:`4441`)
* (GNU/Linux) Avoid segfault when temp path is missing. (:issue:`5255`)
* (GNU/Linux) Replace a ``strncpy()`` call in ``pyi_path_dirname()`` with
  ``snprintf()`` to ensure that the resulting string is always null-terminated.
  (:issue:`5212`)
* (OSX) Added capability for already-running apps to accept URL & drag'n drop
  events via Apple Event forwarding (:issue:`5276`)
* (OSX) Bump ``MACOSX_DEPLOYMENT_TARGET`` from 10.7 to 10.13. (:issue:`4627`,
  :issue:`4886`)
* (OSX) Fix to reactivate running app on "reopen" (:issue:`5295`)
* (Windows) Use ``_wfullpath()`` instead of ``_fullpath()`` in
  ``pyi_path_fullpath`` to allow non-ASCII characters in the path.
  (:issue:`5189`)


Documentation
~~~~~~~~~~~~~

* Add zlib to build the requirements in the Building the Bootlooder section of
  the docs. (:issue:`5130`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Add informative message what do to if RecurrsionError occurs.
  (:issue:`4406`, :issue:`5156`)
* Prevent a local directory with clashing name from shadowing a system library.
  (:issue:`5182`)
* Use module loaders to get module content instea of an quirky way semming from
  early Python 2.x times. (:issue:`5157`)
* (OSX) Exempt the ``Tcl``/``Tk`` dynamic libraries in the system framework
  from relative path overwrite. Fix missing ``Tcl``/``Tk`` dynlib on older
  python.org builds that still make use of the system framework.
  (:issue:`5172`)


Test-suite and Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Replace ``skipif_xxx`` for platform-specific tests by markers.
  (:issue:`1427`)
* Test/CI: Test failures are automatically retried once. (:issue:`5214`)


Bootloader build
~~~~~~~~~~~~~~~~

* Fix AppImage builds that were broken since PyInstaller 3.6. (:issue:`4693`)
* Update build system to use Python 3.
* OSX: Fixed the ineffectiveness of the ``--distpath`` argument for the
  ``BUNDLE`` step. (:issue:`4892`)
* OSX: Improve codesigning and notarization robustness. (:issue:`3550`,
  :issue:`5112`)
* OSX: Use high resolution mode by default for GUI applications.
  (:issue:`4337`)


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
  (:issue:`4232`, :issue:`4301`, :issue:`4582`).
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
  then entry-point, then PyInstaller builtins. (:issue:`4876`)


Bugfix
~~~~~~

* (AIX) Include python-malloc labeled libraries in search for libpython.
  (:issue:`4738`)
* (win32) Fix Security Alerts caused by subtle implementation differences
  between posix anf windows in ``os.path.dirname()``. (:issue:`4707`)
* (win32) Fix struct format strings for versioninfo. (:issue:`4861`)
* (Windows) cv2: bundle the `opencv_videoio_ffmpeg*.dll`, if available.
  (:issue:`4999`)
* (Windows) GLib: bundle the spawn helper executables for `g_spawn*` API.
  (:issue:`5000`)
* (Windows) PySide2.QtNetwork: search for SSL DLLs in `PrefixPath` in addition
  to `BinariesPath`. (:issue:`4998`)
* (Windows) When building with 32-bit python in onefile mode, set the
  ``requestedExecutionLevel`` manifest key every time and embed the manifest.
  (:issue:`4992`)
* * (AIX) Fix uninitialized variable. (:issue:`4728`, :issue:`4734`)
* Allow building on a different drive than the source. (:issue:`4820`)
* Consider Python<version> as possible library binary path. Fixes issue where
  python is not found if Python3 is installed via brew on OSX (:issue:`4895`)
* Ensure shared dependencies from onefile packages can be opened in the
  bootloader.
* Ensuring repeatable builds of base_library.zip. (:issue:`4654`)
* Fix ``FileNotFoundError`` showing up in ``utils/misc.py`` which occurs when a
  namespace was processed as an filename. (:issue:`4034`)
* Fix multipackaging. The `MERGE` class will now have the correct relative
  paths
  between shared dependencies which can correctly be opened by the bootloader.
  (:issue:`1527`, :issue:`4303`)
* Fix regression when trying to avoid hard-coded paths in .spec files.
* Fix SIGTSTP signal handling to allow typing Ctrl-Z from terminal.
  (:issue:`4244`)
* Update the base library to support encrypting Python bytecode (``--key``
  option) again. Many thanks to Matteo Bertini for finally fixing this.
  (:issue:`2365`, :issue:`3093`, :issue:`3133`, :issue:`3160`,
  :issue:`3198`, :issue:`3316`, :issue:`3619`, :issue:`4241`,
  :issue:`4652`)
* When stripping the leading parts of paths in compiled code objects, the
  longest possible import path will now be stripped. (:issue:`4922`)


Incompatible Changes
~~~~~~~~~~~~~~~~~~~~

* Remove support for Python 2.7. The minimum required version is now Python
  3.5. The last version supporting Python 2.7 was PyInstaller 3.6.
  (:issue:`4623`)
* Many hooks are now part of the new `pyinstaller-hooks-contrib`
  repository. See below for a detailed list.


Hooks
~~~~~

* Add hook for ``scipy.stats._stats`` (needed for scipy since 1.5.0).
  (:issue:`4981`)
* Prevent hook-nltk from adding non-existing directories. (:issue:`3900`)
* Fix ``importlib_resources`` hook for modern versions (after 1.1.0).
  (:issue:`4889`)
* Fix hidden imports in `pkg_resources`__ and `packaging`__  (:issue:`5044`)

  - Add yet more hidden imports to pkg_resources hook.
  - Mirror the pkg_resources hook for packaging which may or may not be
    duplicate of ``pkg_resources._vendor.packaging``.

  __ https://setuptools.readthedocs.io/en/latest/pkg_resources.html
  __ https://packaging.pypa.io/en/latest/

* Update pkg_resources hook for setuptools v45.0.0.
* Add QtQmlModels to included libraries for QtWebEngine on OS X
  (:issue:`4631`).
* Fix detecting Qt5 libraries and dependencies from conda-forge builds
  (:issue:`4636`).
* Add an AssertionError message so that users who get an error due
  to Hook conflicts can resolve it (:issue:`4626`).

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
  :issue:`4704`), argon2 (:issue:`4625`) bcrypt. (:issue:`4735`),
  (Bluetooth Low Energy platform Agnostic Klient for Python) (:issue:`4649`)
  jaraco.text (:issue:`4576`, :issue:`4632`), LightGBM. (:issue:`4634`),
  xmldiff (:issue:`4680`), puremagic (identify a file based off it's magic
  numbers) (:issue:`4709`) webassets (:issue:`4760`), tensorflow_core (to
  support tensorflow module forwarding logic (:issue:`4400`, :issue:`4704`)

* These changes have been applied to hooks now moved to the new
  `pyinstaller-hooks-contrib` repository

  - Update Bokeh hook for v2.0.0. (:issue:`4742`, :issue:`4746`)
  - Fix shapely hook on Windows for non-conda shapely installations.
    (:issue:`2834`, :issue:`4749`)


Bootloader
~~~~~~~~~~

* Rework bootloader from using strcpy/strncpy with "is this string
  terminated"-check to use snprintf(); check success at more places. (This
  started from fixing GCC warnings for strncpy and strncat.)
* Fix: When copying files, too much data was copied in most cases. This
  corrupted the file and inhibited using shared dependencies. (:issue:`4303`)
* In debug and windowed mode, show the traceback in dialogs to help debug
  pyiboot01_bootstrap errors. (:issue:`4213`, :issue:`4592`)
* Started a small test-suite for bootloader basic functions. (:issue:`4585`)


Documentation
~~~~~~~~~~~~~

* Add platform-specific usage notes and bootloader build notes for AIX.
  (:issue:`4731`)


PyInstaller Core
~~~~~~~~~~~~~~~~

* Provide setuptools entrypoints to enable other packages to provide
  PyInstaller hooks specific to that package, along with tests for these hooks.
  See https://github.com/pyinstaller/hooksample for more information.
  (:issue:`4232`, :issue:`4582`)


Bootloader build
~~~~~~~~~~~~~~~~

* (AIX) The argument -X32 or -X64 is not recognized by the AIX loader - so this
  code needs to be removed. (:issue:`4730`, :issue:`4731`)
* (OSX) Allow end users to override MACOSX_DEPLOYMENT_TARGET and
  mmacosx-version-min
  via environment variables and set 10.7 as the fallback value for both.
  (:issue:`4677`)
* Do not print info about ``--noconfirm`` when option is already being used.
  (:issue:`4727`)
* Update :command:`waf` to version 2.0.20 (:issue:`4839`)



Older Versions
-----------------

.. toctree::
   :maxdepth: 1
   :caption: Older Versions

   CHANGES-3
   CHANGES-2
   CHANGES-1

.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
