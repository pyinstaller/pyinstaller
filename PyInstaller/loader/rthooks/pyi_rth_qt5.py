#-----------------------------------------------------------------------------
# Copyright (c) 2014-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# PyQt5 exposes the PyQt5.Qt module which contains symbols from all other PyQt5
# packages. PyQt5 uses Python's C API to import all modules and merge their
# contents with PyQt5.Qt (see the generated sipQtcmodule.c file when compiling
# PyQt5), but due to a bug in PyQt, it seems to skip all import-hooks machinery.
#
# Here, we replicate what PyQt does but using native Python code, which we know
# won't bypass the import hooks mechanism described in PEP-302.

PYQT_PACKAGE = 'PyQt5'

# Since we don't know which modules were built into PyQt5 beforehand, this list
# contains all possible modules we are interested to expose through PyQt5.Qt.
PYQT_MODULES = [
    'QAxContainer',
    'QtBluetooth',
    'QtCore',
    'QtDBus',
    'QtDesigner',
    'QtGui',
    'QtHelp',
    'QtMacExtras',
    'QtMultimedia',
    'QtMultimediaWidgets',
    'QtNetwork',
    'QtOpenGL',
    'QtPositioning',
    'QtPrintSupport',
    'QtQml',
    'QtQuick',
    'QtQuickWidgets',
    'QtSensors',
    'QtSerialPort',
    'QtSql',
    'QtSvg',
    'QtTest',
    'QtWebKit',
    'QtWebKitWidgets',
    'QtWebSockets',
    'QtWebEngineWidgets',
    'QtWebChannel',
    'QtWidgets',
    'QtWinExtras',
    'QtX11Extras',
    'QtXmlPatterns',
]

qt_module_obj = __import__('PyQt5.Qt').__dict__['Qt']

for module_name in PYQT_MODULES:
    try:
        # This is always the top-level 'PyQt5' module.
        top_level_module_obj = __import__(PYQT_PACKAGE + '.' + module_name)

        # Grab the module we are interested in from the top-level module
        module_obj = top_level_module_obj.__dict__[module_name]

        # Merge symbols exported by the module with PyQt5.Qt
        qt_module_obj.__dict__.update(module_obj.__dict__)
    except ImportError:
        # It is OK if some module is missing. E.g.: QtMacExtras is built only on
        # OS X and QtWinExtras is built only on Windows.
        pass
