#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import os
import nltk

datas = []
# loop through the data directories and add them
for p in nltk.data.path:
    if(os.path.exists(p)):
        datas.append((p, "nltk_data"))

del nltk.data.path[:]
nltk.data.path = datas
#add the path to nltk_data
nltk.data.path.append(os.path.join(sys._MEIPASS, "nltk_data"))
