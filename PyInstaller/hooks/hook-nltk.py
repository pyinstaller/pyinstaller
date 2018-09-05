#-----------------------------------------------------------------------------
# Copyright (c) 2015-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import nltk

# loop through the nltk data path, then add them as the data directory
datas = []
for p in nltk.data.path:
    datas.append((p, "nltk_data"))

# nltk.chunk.named_entity should be included as name entity chunking doesnt work without it
hiddenimports = ["nltk.chunk.named_entity"]
