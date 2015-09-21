#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Make .eggs and zipfiles available at runtime

import os
import sys

d = "eggs"
d = os.path.join(sys._MEIPASS, d)

# Test if the `eggs´ directory exists. This allows to
# opportunistically including this script into the packaged exe, even
# if no eggs as found when packaging the program. (Which may be a
# use-case, see issue #653.
if os.path.isdir(d):
    for fn in os.listdir(d):
        sys.path.append(os.path.join(d, fn))
