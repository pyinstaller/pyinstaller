#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


def _pyi_bootstrap():
    #-- Start bootstrap process
    # Only python built-in modules and modules from base_library.zip can be used at this point.

    import sys  # built-in
    import os  # base_library.zip

    # Extend Python import machinery with our importer(s).
    import pyimod02_importers
    pyimod02_importers.install()

    #-- Bootstrap process is complete.
    # We can now use python modules that were collected into PYZ archive.

    # Let other python modules know that the code is running in frozen mode.
    if not hasattr(sys, 'frozen'):
        sys.frozen = True

    # NOTE: sys._MEIPASS is set by the bootloader.

    # Some packages behave differently when running inside virtual environment. E.g., IPython tries to append path
    # VIRTUAL_ENV to sys.path. For the frozen app we want to prevent this behavior.
    VIRTENV = 'VIRTUAL_ENV'
    if VIRTENV in os.environ:
        # On some platforms (e.g., AIX) 'os.unsetenv()' is unavailable and deleting the var from os.environ does not
        # delete it from the environment.
        os.environ[VIRTENV] = ''
        del os.environ[VIRTENV]

    # At least on Windows, Python seems to hook up the codecs on this import, so it is not enough to just package up all
    # the encodings.
    #
    # It was also reported that without 'encodings' module, the frozen executable fails to load in some configurations:
    # http://www.pyinstaller.org/ticket/651
    #
    # Importing 'encodings' module in a run-time hook is not enough, since some run-time hooks require this module, and
    # the order of running the code from the run-time hooks is not defined.
    try:
        import encodings
    except ImportError:
        encodings = None

    # Starting with python 3.15.0b1, the `encodings` package is frozen (in the cpython sense), along with some of its
    # submodules; see https://github.com/python/cpython/commit/0012686d92fe51f426bcd6797e2f2a50ad4ac74. Consequently,
    # the `encodings/__init__.pyc` module from our `base_library.zip` is not used anymore, and so the `encodings`
    # directory in our base library archive is not searched, albeit it contains all non-frozen encoding modules.
    # Therefore, we need to manually add that directory to `encodings.__path__`, otherwise we end up missing support
    # for most of encodings.
    if encodings and hasattr(encodings, '__path__'):
        encodings_dir = os.path.join(sys._MEIPASS, 'base_library.zip', 'encodings')
        if encodings_dir not in encodings.__path__:
            encodings.__path__.append(encodings_dir)

    # In the Python interpreter 'warnings' module is imported when 'sys.warnoptions' is not empty. Mimic this behavior.
    if sys.warnoptions:
        try:
            import warnings  # noqa: F401
        except ImportError:
            pass

    # Install the hooks for ctypes
    import pyimod03_ctypes  # noqa: E402
    pyimod03_ctypes.install()

    # Install the hooks for pywin32 (Windows only)
    if sys.platform.startswith('win'):
        import pyimod04_pywin32
        pyimod04_pywin32.install()

    # Apply a hack for metadata that was collected from (unzipped) python eggs; the EGG-INFO directories are collected
    # into their parent directories (my_package-version.egg/EGG-INFO), and for metadata to be discoverable by
    # `importlib.metadata`, the .egg directory needs to be in `sys.path`. The deprecated `pkg_resources` does not have
    # this limitation, and seems to work as long as the .egg directory's parent directory (in our case `sys._MEIPASS`
    # is in `sys.path`).
    for entry in os.listdir(sys._MEIPASS):
        entry = os.path.join(sys._MEIPASS, entry)
        if not os.path.isdir(entry):
            continue
        if entry.endswith('.egg'):
            sys.path.append(entry)


_pyi_bootstrap()
del _pyi_bootstrap
