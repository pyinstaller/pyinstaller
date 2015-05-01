#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
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
import glob
import os
import itertools
from PyInstaller.hooks.hookutils import collect_submodules

hiddenimports = ['zmq.utils.garbage']
hiddenimports.extend(collect_submodules('zmq.backend'))

def hook(mod):
    # If PyZMQ provides its own copy of libzmq or libsodium, add it to the
    # extension-modules TOC so zmq/__init__.py can load it at runtime.
    # For predictable behavior, the libzmq search here must be equivalent
    # to the search in zmq/__init__.py.
    zmq_directory = os.path.dirname(mod.__file__)
    # search for libzmq*.{pyd,so,dll,dylib}* and libsodium*.{pyd,so,dll,dylib}*
    for libname, ext in itertools.product(('libzmq', 'libsodium'),
                                          ('pyd', 'so', 'dll', 'dylib')):
        bundled = glob.glob(os.path.join(zmq_directory, libname + '.' + ext))
        if bundled:
            # zmq/__init__.py will look in os.join(sys._MEIPASS, 'zmq'),
            # so libzmq has to land there.
            name = os.path.join('zmq', os.path.basename(bundled[0]))
            # TODO fix this hook to use attribute 'binaries'.
            mod.pyinstaller_binaries.append((name, bundled[0], 'BINARY'))

    return mod
