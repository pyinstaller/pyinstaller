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
import sys


hiddenimports = [
    'zmq.core.pysocket',
    'zmq.utils.jsonapi',
    'zmq.utils.strtypes',
]


def hook(mod):
    # If PyZMQ provides its own copy of libzmq, add it to the
    # extension-modules TOC so zmq/__init__.py can load it at runtime.
    # For predictable behavior, the libzmq search here must be identical
    # to the search in zmq/__init__.py.
    zmq_directory = os.path.dirname(mod.__file__)
    for ext in ('pyd', 'so', 'dll', 'dylib'):
        bundled = glob.glob(os.path.join(zmq_directory, 'libzmq*.%s*' % ext))
        if bundled:
            # zmq/__init__.py will look in os.join(sys._MEIPASS, 'zmq'),
            # so libzmq has to land there.
            name = os.path.join('zmq', os.path.basename(bundled[0]))
            mod.binaries.append((name, bundled[0], 'BINARY'))
            break

    return mod
