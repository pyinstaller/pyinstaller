#-----------------------------------------------------------------------------
# Copyright (c) 2015-2021, PyInstaller Development Team.
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

os.environ['GTK_DATA_PREFIX'] = sys._MEIPASS
os.environ['GTK_EXE_PREFIX'] = sys._MEIPASS
os.environ['GTK_PATH'] = sys._MEIPASS

# Include these here, as GTK will import pango automatically
os.environ['PANGO_LIBDIR'] = sys._MEIPASS
os.environ['PANGO_SYSCONFDIR'] = os.path.join(sys._MEIPASS, 'etc') # TODO?
