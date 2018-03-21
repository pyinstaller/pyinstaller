#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Verify packaging of Sphinx, which relies on jinja2 and on docutils. Sphinx and
# docutils rely on data files in their module directories, which their
# respective hook scripts must find and copy.

# Library imports
# ---------------
import sys
import os.path

# Third-party imports
# -------------------
import sphinx.cmd.build

# Local imports
# -------------
from pyi_get_datadir import get_data_dir

sphinx_path = os.path.join(get_data_dir(), 'sphinx')

# Invoke Sphinx. See
# http://sphinx-doc.org/invocation.html#invocation-of-sphinx-build for more
# details of the options below.
ret = sphinx.cmd.build.main([
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
