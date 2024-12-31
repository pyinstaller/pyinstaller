#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Verify packaging of Sphinx, which relies on jinja2 and on docutils. Sphinx and docutils rely on data files in their
# module directories, which their respective hook scripts must find and copy.

import os
import sys

import sphinx.cmd.build

# The path to source data directory is passed via first command-line argument.
if len(sys.argv) != 2:
    print(f"Use: {sys.argv[0]} <data-dir>")
    raise SystemExit(1)
sphinx_path = sys.argv[1]

# Invoke Sphinx. See http://sphinx-doc.org/invocation.html#invocation-of-sphinx-build for more details
# on the used options.
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
    os.path.join(sphinx_path, '_build', 'html')
])  # yapf: disable
raise SystemExit(ret)
