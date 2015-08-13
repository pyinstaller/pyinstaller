#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

if sys.platform == 'darwin':
    from ctypes.macholib.dyld import DEFAULT_LIBRARY_FALLBACK
    # Insert sys._MEIPASS in the first position of the list of paths that ctypes uses to search for libraries
    DEFAULT_LIBRARY_FALLBACK.insert(0, sys._MEIPASS)

    import enchant

    # Set the path enchant uses to look for myspell dictionaries to be in our executable
    # TODO check if this is needed on windows
    enchant.set_param('enchant.myspell.dictionary.path', os.path.join(sys._MEIPASS, 'share', 'enchant', 'myspell'))
