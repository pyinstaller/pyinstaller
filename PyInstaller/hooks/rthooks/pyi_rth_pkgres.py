#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import os
import sys
import pathlib

import pkg_resources
from pyimod03_importers import FrozenImporter

SYS_PREFIX = pathlib.PurePath(sys._MEIPASS)


# To make pkg_resources work with frozen modules we need to set the 'Provider'
# class for FrozenImporter. This class decides where to look for resources
# and other stuff. 'pkg_resources.NullProvider' is dedicated to PEP302
# import hooks like FrozenImporter is. It uses method __loader__.get_data() in
# methods pkg_resources.resource_string() and pkg_resources.resource_stream()
#
# We subclass the NullProvider and implement _has(), _isdir(), and _listdir(),
# which are needed for pkg_resources.resource_exists(), resource_isdir(),
# and resource_listdir() to work. We cannot use the DefaultProvider,
# because it provides filesystem-only implementations (and overrides _get()
# with a filesystem-only one), whereas our provider needs to also support
# embedded resources.


class _TocFilesystem:
    def __init__(self, toc_files, toc_dirs=[]):
        # Reconstruct the fileystem hierarchy by building a prefix tree from
        # the given file and directory paths
        self._tree = dict()

        # Data files
        for path in toc_files:
            path = pathlib.PurePath(path)
            current = self._tree
            for component in path.parts[:-1]:
                current = current.setdefault(component, {})
            current[path.parts[-1]] = ''

        # Extra directories
        for path in toc_dirs:
            path = pathlib.PurePath(path)
            current = self._tree
            for component in path.parts:
                current = current.setdefault(component, {})

    def _get_tree_node(self, path):
        path = pathlib.PurePath(path)
        current = self._tree
        for component in path.parts:
            if component not in current:
                return None
            current = current[component]
        return current

    def path_exists(self, path):
        node = self._get_tree_node(path)
        return node is not None  # File or directory

    def path_isdir(self, path):
        node = self._get_tree_node(path)
        if node is None:
            return False  # Non-existant
        if isinstance(node, str):
            return False  # File
        return True

    def path_listdir(self, path):
        node = self._get_tree_node(path)
        if not isinstance(node, dict):
            return []  # Non-existant or file
        return list(node.keys())


class PyiFrozenProvider(pkg_resources.NullProvider):
    def __init__(self, module):
        super().__init__(module)

        # Get top-level path; if "module" corresponds to a package,
        # we need the path to the package itself. If "module" is a
        # submodule in a package, we need the path to the parent
        # package.
        self._pkg_path = pathlib.PurePath(module.__file__).parent

        # Defer initialization of PYZ-embedded resources tree to the
        # first access
        self._embedded_tree = None

    @property
    def embedded_tree(self):
        if self._embedded_tree is None:
            # Construct a path relative to _MEIPASS directory for searching
            # the TOC
            rel_pkg_path = self._pkg_path.relative_to(SYS_PREFIX)

            # Reconstruct package name prefix (use package path to obtain
            # correct prefix in case of a module)
            pkg_name = '.'.join(rel_pkg_path.parts)

            # Collect relevant entries from TOC. We are interested in either
            # files that are located in the package/module's directory (data
            # files) or in packages that are prefixed with package/module's
            # name (to reconstruct subpackage directories)
            data_files = []
            package_dirs = []
            for entry in self.loader.toc:
                entry_path = pathlib.PurePath(entry)
                if rel_pkg_path in entry_path.parents:
                    # Data file path
                    data_files.append(entry_path)
                elif entry.startswith(pkg_name) and self.loader.is_package(entry):
                    # Package or subpackage; convert the name to directory path
                    package_dir = pathlib.PurePath(*entry.split('.'))
                    package_dirs.append(package_dir)

            # Reconstruct the filesystem
            self._embedded_tree = _TocFilesystem(data_files, package_dirs)
        return self._embedded_tree

    def _normalize_path(self, path):
        # Avoid using Path.resolve(), because it resolves symlinks. This
        # is undesirable, because the pure path in self._pkg_path does
        # not have symlinks resolved, so comparison between the two
        # would be faulty. So use os.path.abspath() instead to normalize
        # the path
        return pathlib.Path(os.path.abspath(path))

    def _is_relative_to_package(self, path):
        return path == self._pkg_path or self._pkg_path in path.parents

    def _has(self, path):
        # Prevent access outside the package
        path = self._normalize_path(path)
        if not self._is_relative_to_package(path):
            return False

        # Check the filesystem first to avoid unnecessarily computing
        # the relative path...
        if path.exists():
            return True
        rel_path = path.relative_to(SYS_PREFIX)
        return self.embedded_tree.path_exists(rel_path)

    def _isdir(self, path):
        # Prevent access outside the package
        path = self._normalize_path(path)
        if not self._is_relative_to_package(path):
            return False

        # Embedded resources have precedence over filesystem...
        rel_path = path.relative_to(SYS_PREFIX)
        node = self.embedded_tree._get_tree_node(rel_path)
        if node is None:
            return path.is_dir()  # No match found; try the filesystem
        else:
            # str = file, dict = directory
            return not isinstance(node, str)

    def _listdir(self, path):
        # Prevent access outside the package
        path = self._normalize_path(path)
        if not self._is_relative_to_package(path):
            return []

        # Relative path for searching embedded resources
        rel_path = path.relative_to(SYS_PREFIX)
        # List content from embedded filesystem...
        content = self.embedded_tree.path_listdir(rel_path)
        # ... as well as the actual one
        if path.is_dir():
            # Use os.listdir() to avoid having to convert Path objects
            # to strings... Also make sure to de-duplicate the results
            path = str(path)  # not is_py36
            content = list(set(content + os.listdir(path)))
        return content


pkg_resources.register_loader_type(FrozenImporter, PyiFrozenProvider)
