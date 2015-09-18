#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
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

# If PyZMQ provides its own copy of libzmq or libsodium, add it to the
# extension-modules TOC so zmq/__init__.py can load it at runtime.
# For predictable behavior, the libzmq search here must be equivalent
# to the search in zmq/__init__.py.
# zmq/__init__.py will look in os.join(sys._MEIPASS, 'zmq'),
# so libzmq has to land there.
binaries = collect_dynamic_libs('zmq')
