# -----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
"""
Avro is a serialization and RPC framework.
"""

import os
from PyInstaller.utils.hooks import get_module_file_attribute
from PyInstaller.compat import is_py3


res_loc = os.path.dirname(get_module_file_attribute("avro"))
if is_py3:
    # see https://github.com/apache/avro/blob/master/lang/py3/setup.py
    datas = [
        # Include the version.txt file, used to set __version__
        (os.path.join(res_loc, "VERSION.txt"), "avro"),
        # The handshake schema is needed for IPC communication
        (os.path.join(res_loc, "HandshakeRequest.avsc"), "avro"),
        (os.path.join(res_loc, "HandshakeResponse.avsc"), "avro"),
    ]
else:
    # on python 2 everything is bundled https://github.com/apache/avro/blob/master/lang/py/setup.py
    datas = []
