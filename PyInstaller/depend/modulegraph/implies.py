#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Implicit ("implied") dependencies between Python modules.

Some imports are invisible to bytecode scanning:

* C extensions and builtins import other modules from C code -- there is no
  Python bytecode to scan (``time`` pulls in ``_strptime``, ``_ssl`` pulls
  in ``socket``, ...).
* Some names are not real modules at all, but aliases (``os.path`` is
  ``posixpath``/``ntpath`` depending on the platform).

``get_implies()`` returns the curated mapping covering these cases. The
graph engine consults it (via the ``implies=`` constructor argument) every
time it finishes processing one of the mapped modules, and queues the listed
dependencies as imports of that module.

This data was previously maintained in the vendored ``modulegraph`` library
(``PyInstaller/lib/modulegraph/find_modules.py``); it moves here as part of
bringing the graph in-tree.
"""

# NOTE: pkgutil is needed for the xml.etree helper inside get_implies().
import os
import pkgutil

from PyInstaller.depend.modulegraph.nodes import Alias


def get_implies():
    """
    Return the mapping of module name -> modules it implicitly imports.

    Values are either:

    * a list of fully-qualified module names to queue as imports of the
      mapped module,
    * an :class:`~.nodes.Alias` marking the mapped name as an alias for
      another module, or
    * ``None`` to indicate the module's imports are untrackable and should
      be skipped entirely (e.g. ``_frozen_importlib`` is part of the
      interpreter itself).
    """

    def _xml_etree_modules():
        import xml.etree
        return [
            f"xml.etree.{module_name}"
            for _, module_name, is_package in pkgutil.iter_modules(xml.etree.__path__)
            if not is_package
        ]

    return {
        # imports done from C code in built-in and/or extension modules
        # (untrackable by modulegraph).
        "_curses": ["curses"],
        "posix": ["resource"],
        "gc": ["time"],
        "time": ["_strptime"],
        "datetime": ["time"],
        "parser": ["copyreg"],
        "codecs": ["encodings"],
        "_sre": ["copy", "re"],
        "zipimport": ["zlib"],

        # _frozen_importlib is part of the interpreter itself
        "_frozen_importlib": None,

        # os.path is an alias for a platform specific module,
        # ensure that the graph shows this.
        "os.path": Alias(os.path.__name__),

        # Python >= 3.2:
        "_datetime": ["time", "_strptime"],
        "_json": ["json.decoder"],
        "_pickle": ["codecs", "copyreg", "_compat_pickle"],
        "_posixsubprocess": ["gc"],
        "_ssl": ["socket"],

        # Python >= 3.3:
        "_elementtree": ["pyexpat"] + _xml_etree_modules(),

        # This is not C extension, but it uses __import__
        "anydbm": ["dbhash", "gdbm", "dbm", "dumbdbm", "whichdb"],

        # Known package aliases
        "wxPython.wx": Alias('wx'),
    }
