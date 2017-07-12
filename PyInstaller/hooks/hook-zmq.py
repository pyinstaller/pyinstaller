#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
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
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

hiddenimports = ['zmq.utils.garbage']
hiddenimports.extend(collect_submodules('zmq.backend'))

# If PyZMQ provides its own copy of libzmq and libsodium, add it to the
# extension-modules TOC so zmq/__init__.py can load it at runtime.
# PyZMQ is able to load 'libzmq' and 'libsodium' even from sys._MEIPASS.
# So they could be with other .dlls.
binaries = collect_dynamic_libs('zmq')

# If PyZMQ pvorides its own copy of libzmq and libsodium, these libs look like
# C extensions. Excluding these modules ensures that those dlls are not bundled
# twice. Once as ./zmq.libzmq.pyd and once as ./zmq/libzmq.py.
excludedimports = ['zmq.libzmq']
