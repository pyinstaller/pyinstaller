#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Markdown uses __import__ed extensions. Make sure these work by trying to use the 'toc' extension..
import markdown
print(markdown.markdown('testing',  ['toc']))
