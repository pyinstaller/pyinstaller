#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Hooks to make ctypes.CDLL, .PyDLL, etc. look in sys._MEIPASS first.
"""

import sys

def install():
    """Install the hooks.

    This can not be done at module-level, since the import machinery is not
    setup completely when this module is executed.
    """

    import os
    try:
        import ctypes
        from ctypes import LibraryLoader, DEFAULT_MODE

        def _frozen_name(name):
            if name:
                frozen_name = os.path.join(sys._MEIPASS, os.path.basename(name))
                if os.path.exists(frozen_name):
                    name = frozen_name
            return name

        class PyInstallerImportError(OSError):
            def __init__(self, name):
                self.msg = ("Failed to load dynlib/dll %r. "
                            "Most probably this dynlib/dll was not found "
                            "when the application was frozen.") % name
                self.args = (self.msg,)

        class PyInstallerCDLL(ctypes.CDLL):
            def __init__(self, name, *args, **kwargs):
                name = _frozen_name(name)
                try:
                    super(PyInstallerCDLL, self).__init__(name, *args, **kwargs)
                except Exception as base_error:
                    raise PyInstallerImportError(name)

        ctypes.CDLL = PyInstallerCDLL
        ctypes.cdll = LibraryLoader(PyInstallerCDLL)

        class PyInstallerPyDLL(ctypes.PyDLL):
            def __init__(self, name, *args, **kwargs):
                name = _frozen_name(name)
                try:
                    super(PyInstallerPyDLL, self).__init__(name, *args, **kwargs)
                except Exception as base_error:
                    raise PyInstallerImportError(name)

        ctypes.PyDLL = PyInstallerPyDLL
        ctypes.pydll = LibraryLoader(PyInstallerPyDLL)

        if sys.platform.startswith('win'):
            class PyInstallerWinDLL(ctypes.WinDLL):
                def __init__(self, name,*args, **kwargs):
                    name = _frozen_name(name)
                    try:
                        super(PyInstallerWinDLL, self).__init__(name, *args, **kwargs)
                    except Exception as base_error:
                        raise PyInstallerImportError(name)

            ctypes.WinDLL = PyInstallerWinDLL
            ctypes.windll = LibraryLoader(PyInstallerWinDLL)

            class PyInstallerOleDLL(ctypes.OleDLL):
                def __init__(self, name,*args, **kwargs):
                    name = _frozen_name(name)
                    try:
                        super(PyInstallerOleDLL, self).__init__(name, *args, **kwargs)
                    except Exception as base_error:
                        raise PyInstallerImportError(name)

            ctypes.OleDLL = PyInstallerOleDLL
            ctypes.oledll = LibraryLoader(PyInstallerOleDLL)

    except ImportError:
        # ctypes is not frozen in this application
        pass

# On Mac OS X insert sys._MEIPASS in the first position of the list of paths
# that ctypes uses to search for libraries.
#
# Note: 'ctypes' module will NOT be bundled with every app because code in this
#       module is not scanned for module dependencies. It is safe to wrap
#       'ctypes' module into 'try/except ImportError' block.
if sys.platform.startswith('darwin'):
    try:
        from ctypes.macholib import dyld
        dyld.DEFAULT_LIBRARY_FALLBACK.insert(0, sys._MEIPASS)
    except ImportError:
        # Do nothing when module 'ctypes' is not available.
        pass
