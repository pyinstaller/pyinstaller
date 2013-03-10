#
# Copyright (C) 2012, Bryan A. Jones
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Verify packaging of Sphinx, which relies on jinja2 and on docutils. Sphinx and docutils rely on data files in their module directories, which their respective hook scripts must find and copy.

import sphinx, sys
# See http://sphinx.pocoo.org/invocation.html#invocation for more details of 
# the options below.
#
# Also, note that this is run in the dist/test_sphihnx direcotry, but uses
# conf.py and index.rst from the sphinx/ subdirectory, so the command-line
# options uses '../../sphinx' to refer to these files.
ret = sphinx.main(['', # First param is name of program (anything is fine)
                   '-a', '-E',  # Rebuild all files
                   '-b', 'html', # -b html produces html output
                   '-d', '_build/doctrees', # Specify an output directory
                                            # for data files
                   '-c', '../../sphinx', # Specify the directory where
                                         #  conf.py lives
                   '../../sphinx', # Location of the source (index.rst)
                   '_build/html' # Output directory for the resulting HTML
                                 # files
                     ])
sys.exit(ret)