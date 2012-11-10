#
# Copyright (C) 2011, Vinay Sajip
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Hook for PyZMQ. Cython based Python bindings for messaging library ZeroMQ.
# http://www.zeromq.org/


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
