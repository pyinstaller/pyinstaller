#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------
#
# This rthook overrides pkgutil.iter_modules with custom implementation
# that uses PyInstaller's FrozenImporter to list sub-modules embedded
# in the PYZ archive. The non-embedded modules (binary extensions, or
# .pyc modules in noarchive build) are handled by original pkgutil
# iter_modules implementation (and consequently, python's FileFinder).
#
# The preferred way of adding support for iter_modules would be adding
# non-standard iter_modules() method to FrozenImporter itself. However,
# that seems to work only for path entry finders (for use with sys.path_hooks),
# while PyInstaller's FrozenImporter is registered as meta path finders
# (for use with sys.meta_path). Turning FrozenImporter into path entry
# finder, would seemingly require the latter to support on-filesystem
# resources (e.g., extension modules) in addition to PYZ-embedded ones.
#
# Therefore, we instead opt for overriding pkgutil.iter_modules with
# custom implementation that augments the output of original
# implementation with contents of PYZ archive from FrozenImporter's TOC.


import os
import sys

import pkgutil

from pyimod03_importers import FrozenImporter


_orig_pkgutil_iter_modules = pkgutil.iter_modules


def _pyi_pkgutil_iter_modules(path=None, prefix=''):
    # Use original implementation to discover on-filesystem
    # modules (binary extensions in regular builds, or both binary
    # extensions and compiled pyc modules in noarchive debug builds)
    yield from _orig_pkgutil_iter_modules(path, prefix)

    # Find the instance of PyInstaller's FrozenImporter
    for importer in pkgutil.iter_importers():
        if isinstance(importer, FrozenImporter):
            break
    else:
        return

    if not path:
        # Search for all top-level packages/modules. These will have
        # no dots in their entry names
        for entry in importer.toc:
            if entry.count('.') != 0:
                continue
            is_pkg = importer.is_package(entry)
            yield pkgutil.ModuleInfo(importer, prefix + entry, is_pkg)
    else:
        # Declare SYS_PREFIX locally, to avoid clash with eponymous
        # global symbol from pyi_rth_pkgutil hook.
        SYS_PREFIX = sys._MEIPASS + os.path.sep
        SYS_PREFIXLEN = len(SYS_PREFIX)
        # Only single path is supported, and it must start with
        # sys._MEIPASS
        pkg_path = os.path.normpath(path[0])
        assert pkg_path.startswith(SYS_PREFIX)
        # Construct package prefix from path...
        pkg_prefix = pkg_path[SYS_PREFIXLEN:]
        pkg_prefix = pkg_prefix.replace(os.path.sep, '.')
        # ... and ensure it ends with a dot (so we can directly filter
        # out the package itself)
        if not pkg_prefix.endswith('.'):
            pkg_prefix += '.'
        pkg_prefix_len = len(pkg_prefix)

        for entry in importer.toc:
            if not entry.startswith(pkg_prefix):
                continue
            name = entry[pkg_prefix_len:]
            if name.count('.') != 0:
                continue
            is_pkg = importer.is_package(entry)
            yield pkgutil.ModuleInfo(importer, prefix + name, is_pkg)


pkgutil.iter_modules = _pyi_pkgutil_iter_modules
