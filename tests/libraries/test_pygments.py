#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Pyinstaller executables fail without these imports; Python doesn't need them.
import pygments.formatters
import pygments.lexers

# This sample code is taken from http://pygments.org/docs/quickstart/.
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

code = 'print "Hello World"'
print highlight(code, PythonLexer(), HtmlFormatter())

