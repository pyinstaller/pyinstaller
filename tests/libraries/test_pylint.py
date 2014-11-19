#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from pylint.lint import Run

# The following more obvious test doesn't work::
#
#   import pylint, sys
#
#   pylint.run_pylint()
#   sys.exit(0)
#
# because pylint will override the sys.exit value with 32, since a valid command
# line wasn't given. Instead, provide a valid command line below.
Run(['-h'])
