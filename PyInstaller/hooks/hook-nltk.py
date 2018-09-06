#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# hook for nltk
import nltk
from PyInstaller.utils.hooks import collect_data_files

# add datas for nltk
datas = collect_data_files('nltk', False)

# loop through the data directories and add them
for p in nltk.data.path:
    datas.append((p, "nltk_data"))

# nltk.chunk.named_entity should be included
hiddenimports = ["nltk.chunk.named_entity"]
