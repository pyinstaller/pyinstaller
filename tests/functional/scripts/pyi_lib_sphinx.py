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
import sys
# See http://sphinx.pocoo.org/invocation.html#invocation for more details of
# the options below.
#
# Also, note that this is run in the dist/test_sphinx directory, but uses
# conf.py and index.rst from the sphinx/ subdirectory, so the command-line
# options uses the path in argv[1] to refer to these files.
sphinx_path = sys.argv[1]
ret = sphinx.main([
   # First param is name of program (anything is fine).
   '',
   # Rebuild all files.
   '-a', '-E',
   # Produce html output.
   '-b', 'html',
   # Specify an output directory for data files
   '-d', '_build/doctrees',
   # Specify the directory where conf.py lives.
   '-c', sphinx_path,
   # Specify the location of the source (index.rst).
   sphinx_path,
   # Output directory for the resulting HTML files.
   '_build/html'])
raise SystemExit(ret)
