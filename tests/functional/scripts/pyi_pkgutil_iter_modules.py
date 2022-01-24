#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import sys
import argparse
import pkgutil
import importlib

# Argument parser
parser = argparse.ArgumentParser(description="pkgutil iter_modules test")
parser.add_argument(
    'package',
    type=str,
    help="Package to test.",
)
parser.add_argument(
    '--prefix',
    type=str,
    default='',
    help="Optional prefix to pass to iter_modules.",
)
parser.add_argument(
    '--resolve-pkg-path',
    action='store_true',
    default=False,
    help="Resolve symbolic links in package path before passing it to pkgutil.iter_modules.",
)
parser.add_argument(
    '--output-file',
    default=None,
    type=str,
    help="Output file.",
)
args = parser.parse_args()

# Output file (optional)
if args.output_file:
    fp = open(args.output_file, 'w')
else:
    fp = sys.stdout

# Iterate over package's module
package = importlib.import_module(args.package)
pkg_path = package.__path__
if args.resolve_pkg_path:
    pkg_path = [os.path.realpath(path) for path in pkg_path]
for module in pkgutil.iter_modules(pkg_path, args.prefix):
    print("%s;%d" % (module.name, module.ispkg), file=fp)

# Cleanup
if args.output_file:
    fp.close()
