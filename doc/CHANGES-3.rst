Changelog for PyInstaller 3.0 – 3.2.1
======================================================

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

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
