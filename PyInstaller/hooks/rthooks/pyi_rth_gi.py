#-----------------------------------------------------------------------------
# Copyright (c) 2015-2022, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import os
import sys

os.environ['GI_TYPELIB_PATH'] = os.path.join(sys._MEIPASS, 'gi_typelibs')
