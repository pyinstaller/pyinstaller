#-----------------------------------------------------------------------------
# Copyright (c) 2018-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import ssl
import sys

# Use certificate from certifi only if cafile could not find by ssl.
if ssl.get_default_verify_paths().cafile is None:
    os.environ['SSL_CERT_FILE'] = os.path.join(sys._MEIPASS, 'certifi', 'cacert.pem')
