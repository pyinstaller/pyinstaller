#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------
#
# The run-time hook provides a custom module iteration function for our PyiFrozenImporter, which allows
# `pkgutil.iter_modules()` to return entries for modules that are embedded in the PYZ archive. The non-embedded modules
# (binary extensions, modules collected as only source .py files, etc.) are enumerated using the `fallback_finder`
# provided by `PyiFrozenImporter` (which typically would be the python's `FileFinder`).
def _pyi_rthook():
    import pkgutil

    import pyimod02_importers  # PyInstaller's bootstrap module

    # This could, in fact, be implemented as `iter_modules()` method of the `PyiFrozenImporter`. However, we want to
    # avoid importing `pkgutil` in that bootstrap module (i.e., for the `pkgutil.iter_importer_modules()` call on the
    # fallback finder).
    def _iter_pyi_frozen_file_finder_modules(finder, prefix=''):
        # Fetch PYZ TOC tree from pyimod02_importers
        pyz_toc_tree = pyimod02_importers.get_pyz_toc_tree()

        # Finder has already pre-computed the package prefix implied by the search path. Use it to find the starting
        # node in the prefix tree.
        if finder._pyz_entry_prefix:
            pkg_name_parts = finder._pyz_entry_prefix.split('.')
        else:
            pkg_name_parts = []

        tree_node = pyz_toc_tree
        for pkg_name_part in pkg_name_parts:
            tree_node = tree_node.get(pkg_name_part)
            if not isinstance(tree_node, dict):
                # This check handles two cases:
                #  a) path does not exist (`tree_node` is `None`)
                #  b) path corresponds to a module instead of a package (`tree_node` is a leaf node (`str`)).
                tree_node = {}
                break

        # Dump the contents of the tree node.
        for entry_name, entry_data in tree_node.items():
            is_pkg = isinstance(entry_data, dict)
            yield prefix + entry_name, is_pkg

        # If our finder has a fall-back finder available, iterate its modules as well. By using the public
        # `fallback_finder` attribute, we force creation of the fallback finder as necessary.
        # NOTE: we do not care about potential duplicates here, because `pkgutil.iter_modules()` itself
        # keeps track of yielded names for purposes of de-duplication.
        if finder.fallback_finder is not None:
            yield from pkgutil.iter_importer_modules(finder.fallback_finder, prefix)

    pkgutil.iter_importer_modules.register(
        pyimod02_importers.PyiFrozenImporter,
        _iter_pyi_frozen_file_finder_modules,
    )


_pyi_rthook()
del _pyi_rthook
