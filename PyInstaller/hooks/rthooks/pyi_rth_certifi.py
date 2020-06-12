#-----------------------------------------------------------------------------
# Copyright (c) 2018-2020, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import os
import ssl
import sys

# Use certificate from certifi only if cafile could not find by ssl.
if ssl.get_default_verify_paths().cafile is None:
    os.environ['SSL_CERT_FILE'] = os.path.join(sys._MEIPASS, 'certifi', 'cacert.pem')
