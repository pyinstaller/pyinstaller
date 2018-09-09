#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for PyZMQ. Cython based Python bindings for messaging library ZeroMQ.
http://www.zeromq.org/
"""
from PyInstaller.utils.hooks import collect_submodules, get_module_file_attribute
from PyInstaller.compat import is_py2, is_win

hiddenimports = ['zmq.utils.garbage'] + collect_submodules('zmq.backend')

# Python 2 requires use of the ``CExtensionImporter`` in
# ``pyimod03_importers.py``, rather than the standard Python import mechanism
# used by Python 3. This break's PyZMQ's ability to find some of ts extension
# module, requiring the following workaround.
if is_py2:
    # If PyZMQ provides its own copy of libzmq and libsodium, add it to the
    # extension-modules TOC so zmq/__init__.py can load it at runtime.
    # PyZMQ is able to load 'libzmq' and 'libsodium' even from sys._MEIPASS,
    # like they could do with other .dlls.
    try:
        binaries = [(get_module_file_attribute('zmq.libzmq'),
                     '.' if is_win else 'zmq')]
    except ImportError:
        # Not all platforms provide their own copy of libzmq.
        pass
    else:
        # If PyZMQ pvorides its own copy of libzmq and libsodium, these libs look like
        # C extensions. Excluding these modules ensures that those dlls are not bundled
        # twice. Once as ./zmq.libzmq.pyd and once as ./zmq/libzmq.py.
        excludedimports = ['zmq.libzmq']
