#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Verify packaging of Sphinx, which relies on jinja2 and on docutils. Sphinx and
# docutils rely on data files in their module directories, which their
# respective hook scripts must find and copy.

import sphinx
import sys
import os.path

# Sphinx needs input files to operate on. There are two cases:
if getattr(sys, 'frozen', False):
    # 1. Frozen: then the files are in argv[1]/sphinx.
    sphinx_path = sys.argv[1]
else:
    # 2. Not frozen: then the files are in ../data/sphinx.
    sphinx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', 'data')
sphinx_path = os.path.join(sphinx_path, 'sphinx')

# Invoke Sphinx. See
# http://sphinx-doc.org/invocation.html#invocation-of-sphinx-build for more
# details of the options below.
ret = sphinx.main([
   # First param is name of program (anything is fine).
   '',
   # Rebuild all files.
   '-a', '-E',
   # Produce html output.
   '-b', 'html',
   # Specify an output directory for data files.
   '-d', os.path.join(sphinx_path, '_build', 'doctrees'),
   # Specify the location of the source (index.rst).
   sphinx_path,
   # Build directory for the resulting HTML files.
   os.path.join(sphinx_path, '_build', 'html') ])
raise SystemExit(ret)
