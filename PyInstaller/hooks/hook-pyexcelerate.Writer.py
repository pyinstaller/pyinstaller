#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

from pyexcelerate.Writer import _TEMPLATE_PATH
datas = [
	(os.path.join(_TEMPLATE_PATH, '*'), os.path.join('pyexcelerate', 'templates'))
]
