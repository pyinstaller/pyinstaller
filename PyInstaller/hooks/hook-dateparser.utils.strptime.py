#-----------------------------------------------------------------------------
# Copyright (c) 2017-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for dateparser: https://pypi.org/project/dateparser/
from PyInstaller.utils.hooks import exec_statement, collect_submodules

strptime_data_file = exec_statement(
    "import inspect; import _strptime; print(inspect.getfile(_strptime))"
)

datas = [(strptime_data_file, "")]

hiddenimports = collect_submodules('dateparser.data')
print(hiddenimports)
