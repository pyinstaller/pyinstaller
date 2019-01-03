#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules

# Tested on Windows 7 x64 with Python 2.7.6 x32 using ReportLab 3.0
# This has been observed to *not* work on ReportLab 2.7
hiddenimports = collect_submodules('reportlab.pdfbase',
                  lambda name: name.startswith('reportlab.pdfbase._fontdata_'))
