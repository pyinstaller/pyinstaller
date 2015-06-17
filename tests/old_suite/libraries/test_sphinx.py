#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Verify packaging of Sphinx, which relies on jinja2 and on docutils. Sphinx and docutils
# rely on data files in their module directories, which their respective hook scripts must
# find and copy.


import sphinx
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
raise SystemExit(ret)
