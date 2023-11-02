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
# This rthook overrides pkgutil.iter_modules with custom implementation that uses PyInstaller's PyiFrozenImporter to
# list sub-modules embedded in the PYZ archive. The non-embedded modules (binary extensions, or .pyc modules in
# noarchive build) are handled by original pkgutil iter_modules implementation (and consequently, python's FileFinder).
#
# The preferred way of adding support for iter_modules would be adding non-standard iter_modules() method to
# PyiFrozenImporter itself. However, that seems to work only for path entry finders (for use with sys.path_hooks), while
# PyInstaller's PyiFrozenImporter is registered as meta path finders (for use with sys.meta_path). Turning
# PyiFrozenImporter into path entry finder, would seemingly require the latter to support on-filesystem resources
# (e.g., extension modules) in addition to PYZ-embedded ones.
#
# Therefore, we instead opt for overriding pkgutil.iter_modules with custom implementation that augments the output of
# original implementation with contents of PYZ archive from PyiFrozenImporter's TOC.


def _pyi_rthook():
    import os
    import pkgutil
    import sys

    from pyimod02_importers import PyiFrozenImporter

    _orig_pkgutil_iter_modules = pkgutil.iter_modules

    def _pyi_pkgutil_iter_modules(path=None, prefix=''):
        # Use original implementation to discover on-filesystem modules (binary extensions in regular builds, or both
        # binary extensions and compiled pyc modules in noarchive debug builds).
        yield from _orig_pkgutil_iter_modules(path, prefix)

        # Find the instance of PyInstaller's PyiFrozenImporter.
        for importer in pkgutil.iter_importers():
            if isinstance(importer, PyiFrozenImporter):
                break
        else:
            return

        if path is None:
            # Search for all top-level packages/modules. These will have no dots in their entry names.
            for entry in importer.toc:
                if "." in entry:
                    continue
                is_pkg = importer.is_package(entry)
                yield pkgutil.ModuleInfo(importer, prefix + entry, is_pkg)
        else:
            # Use os.path.realpath() to fully resolve any symbolic links in sys._MEIPASS, in order to avoid path
            # mis-matches when the given search paths also contain symbolic links and are already fully resolved.
            # See #6537 for an example of such a problem with onefile build on macOS, where the temporary directory
            # is placed under /var, which is actually a symbolic link to /private/var.
            MEIPASS_PREFIX = os.path.realpath(sys._MEIPASS) + os.path.sep
            MEIPASS_PREFIX_LEN = len(MEIPASS_PREFIX)

            # For macOS .app bundles, the "true" sys._MEIPASS is `name.app/Contents/Frameworks`, but due to
            # cross-linking, we must also consider `name.app/Contents/Resources`. See #7884.
            is_macos_app_bundle = False
            if sys.platform == 'darwin' and sys._MEIPASS.endswith("Contents/Frameworks"):
                ALT_MEIPASS_PREFIX = os.path.realpath(os.path.join(sys._MEIPASS, '..', 'Resources')) + os.path.sep
                ALT_MEIPASS_PREFIX_LEN = len(ALT_MEIPASS_PREFIX)
                is_macos_app_bundle = True

            # Process all given paths
            seen_pkg_prefices = set()
            for pkg_path in path:
                # Fully resolve the given path, in case it contains symbolic links.
                pkg_path = os.path.realpath(pkg_path)

                # Ensure the path ends with os.path.sep; this ensures correct match when the given path is sys._MEIPASS
                # itself (note that we also appended os.path.sep to MEIPASS_PREFIX!). In cases when the given path is
                # a package directory within sys._MEIPASS, the trailing os.path.sep ends up being changed into trailing
                # dot, which allows us to filter the package itself from the results.
                if not pkg_path.endswith(os.path.sep):
                    pkg_path += os.path.sep

                # If the path does not start with sys._MEIPASS, then it cannot be a bundled package.
                # In case of macOS .app bundles, we also need to check the alternative path prefix.
                pkg_prefix = None
                if pkg_path.startswith(MEIPASS_PREFIX):
                    pkg_prefix = pkg_path[MEIPASS_PREFIX_LEN:]
                elif is_macos_app_bundle and pkg_path.startswith(ALT_MEIPASS_PREFIX):
                    pkg_prefix = pkg_path[ALT_MEIPASS_PREFIX_LEN:]
                else:
                    # Given path is outside of sys._MEIPASS.
                    continue

                # Construct package prefix from path remainder. Because we explicitly added os.path.sep to pkg_path
                # earlier, pkg_prefix now contains a trailing dot if necessary.
                pkg_prefix = pkg_prefix.replace(os.path.sep, '.')
                pkg_prefix_len = len(pkg_prefix)

                # If we are given multiple paths and they are either duplicated or resolve to the same package
                # prefix, prevent duplication.
                if pkg_prefix in seen_pkg_prefices:
                    continue
                seen_pkg_prefices.add(pkg_prefix)

                # Check the TOC entries
                if not pkg_prefix:
                    # We are enumerating sys._MEIPASS; return all top-level packages/modules.
                    for entry in importer.toc:
                        if "." in entry:
                            continue
                        is_pkg = importer.is_package(entry)
                        yield pkgutil.ModuleInfo(importer, prefix + entry, is_pkg)
                else:
                    # We are enumerating contents of a package.
                    for entry in importer.toc:
                        if not entry.startswith(pkg_prefix):
                            continue
                        name = entry[pkg_prefix_len:]
                        if "." in name:
                            continue
                        is_pkg = importer.is_package(entry)
                        yield pkgutil.ModuleInfo(importer, prefix + name, is_pkg)

    pkgutil.iter_modules = _pyi_pkgutil_iter_modules


_pyi_rthook()
del _pyi_rthook
