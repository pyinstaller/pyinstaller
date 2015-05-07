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
#   import pylint
#   pylint.run_pylint()
#
# because pylint will exit with 32, since a valid command
# line wasn't given. Instead, provide a valid command line below.

Run(['-h'])
