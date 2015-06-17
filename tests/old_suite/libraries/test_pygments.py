#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test import hooks for the following modules.
from pygments.formatters import HtmlFormatter
# This line must be included for Pyinstaller to work; Python doesn't require it.
import pygments.lexers
from pygments.lexers import PythonLexer
formatter = HtmlFormatter(style='vim')
