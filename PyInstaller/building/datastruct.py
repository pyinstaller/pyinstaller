#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os

from PyInstaller import log as logging
from PyInstaller.building.utils import _check_guts_eq
from PyInstaller.utils import misc

logger = logging.getLogger(__name__)


def unique_name(entry):
    """
    Return the filename used to enforce uniqueness for the given TOC entry.

    Parameters
    ----------
    entry : tuple

    Returns
    -------
    unique_name: str
    """
    name, path, typecode = entry
    if typecode in ('BINARY', 'DATA'):
        name = os.path.normcase(name)

    return name


class TOC(list):
    # TODO: simplify the representation and use directly Modulegraph objects.
    """
    TOC (Table of Contents) class is a list of tuples of the form (name, path, typecode).

    typecode    name                   path                        description
    --------------------------------------------------------------------------------------
    EXTENSION   Python internal name.  Full path name in build.    Extension module.
    PYSOURCE    Python internal name.  Full path name in build.    Script.
    PYMODULE    Python internal name.  Full path name in build.    Pure Python module (including __init__ modules).
    PYZ         Runtime name.          Full path name in build.    A .pyz archive (ZlibArchive data structure).
    PKG         Runtime name.          Full path name in build.    A .pkg archive (Carchive data structure).
    BINARY      Runtime name.          Full path name in build.    Shared library.
    DATA        Runtime name.          Full path name in build.    Arbitrary files.
    OPTION      The option.            Unused.                     Python runtime option (frozen into executable).

    A TOC contains various types of files. A TOC contains no duplicates and preserves order.
    PyInstaller uses TOC data type to collect necessary files bundle them into an executable.
    """
    def __init__(self, initlist=None):
        super().__init__()
        self.filenames = set()
        if initlist:
            for entry in initlist:
                self.append(entry)

    def append(self, entry):
        if not isinstance(entry, tuple):
            logger.info("TOC found a %s, not a tuple", entry)
            raise TypeError("Expected tuple, not %s." % type(entry).__name__)

        unique = unique_name(entry)

        if unique not in self.filenames:
            self.filenames.add(unique)
            super().append(entry)

    def insert(self, pos, entry):
        if not isinstance(entry, tuple):
            logger.info("TOC found a %s, not a tuple", entry)
            raise TypeError("Expected tuple, not %s." % type(entry).__name__)
        unique = unique_name(entry)

        if unique not in self.filenames:
            self.filenames.add(unique)
            super().insert(pos, entry)

    def __add__(self, other):
        result = TOC(self)
        result.extend(other)
        return result

    def __radd__(self, other):
        result = TOC(other)
        result.extend(self)
        return result

    def extend(self, other):
        # TODO: look if this can be done more efficient with out the loop, e.g. by not using a list as base at all.
        for entry in other:
            self.append(entry)

    def __sub__(self, other):
        other = TOC(other)
        filenames = self.filenames - other.filenames
        result = TOC()
        for entry in self:
            unique = unique_name(entry)

            if unique in filenames:
                # Directly use list.append() instead of TOC.append() to avoid unnecessary uniqueness checks.
                # Hence the use of super(TOC, result).
                super(TOC, result).append(entry)
        return result

    def __rsub__(self, other):
        result = TOC(other)
        return result.__sub__(self)


class Target(object):
    invcnum = 0

    def __init__(self):
        from PyInstaller.config import CONF

        # Get a (per class) unique number to avoid conflicts between toc objects
        self.invcnum = self.__class__.invcnum
        self.__class__.invcnum += 1
        self.tocfilename = os.path.join(CONF['workpath'], '%s-%02d.toc' % (self.__class__.__name__, self.invcnum))
        self.tocbasename = os.path.basename(self.tocfilename)
        self.dependencies = TOC()

    def __postinit__(self):
        """
        Check if the target need to be rebuild and if so, re-assemble.

        `__postinit__` is to be called at the end of `__init__` of every subclass of Target. `__init__` is meant to
        setup the parameters and `__postinit__` is checking if rebuild is required and in case calls `assemble()`
        """
        logger.info("checking %s", self.__class__.__name__)
        data = None
        last_build = misc.mtime(self.tocfilename)
        if last_build == 0:
            logger.info("Building %s because %s is non existent", self.__class__.__name__, self.tocbasename)
        else:
            try:
                data = misc.load_py_data_struct(self.tocfilename)
            except Exception:
                logger.info("Building because %s is bad", self.tocbasename)
            else:
                # create a dict for easier access
                data = dict(zip((g[0] for g in self._GUTS), data))
        # assemble if previous data was not found or is outdated
        if not data or self._check_guts(data, last_build):
            self.assemble()
            self._save_guts()

    _GUTS = []

    def _check_guts(self, data, last_build):
        """
        Returns True if rebuild/assemble is required.
        """
        if len(data) != len(self._GUTS):
            logger.info("Building because %s is bad", self.tocbasename)
            return True
        for attr, func in self._GUTS:
            if func is None:
                # no check for this value
                continue
            if func(attr, data[attr], getattr(self, attr), last_build):
                return True
        return False

    def _save_guts(self):
        """
        Save the input parameters and the work-product of this run to maybe avoid regenerating it later.
        """
        data = tuple(getattr(self, g[0]) for g in self._GUTS)
        misc.save_py_data_struct(self.tocfilename, data)


class Tree(Target, TOC):
    """
    This class is a way of creating a TOC (Table of Contents) that describes some or all of the files within a
    directory.
    """
    def __init__(self, root=None, prefix=None, excludes=None, typecode='DATA'):
        """
        root
                The root of the tree (on the build system).
        prefix
                Optional prefix to the names of the target system.
        excludes
                A list of names to exclude. Two forms are allowed:

                    name
                        Files with this basename will be excluded (do not include the path).
                    *.ext
                        Any file with the given extension will be excluded.
        typecode
                The typecode to be used for all files found in this tree. See the TOC class for for information about
                the typcodes.
        """
        Target.__init__(self)
        TOC.__init__(self)
        self.root = root
        self.prefix = prefix
        self.excludes = excludes
        self.typecode = typecode
        if excludes is None:
            self.excludes = []
        self.__postinit__()

    _GUTS = (  # input parameters
        ('root', _check_guts_eq),
        ('prefix', _check_guts_eq),
        ('excludes', _check_guts_eq),
        ('typecode', _check_guts_eq),
        ('data', None),  # tested below
        # no calculated/analysed values
    )

    def _check_guts(self, data, last_build):
        if Target._check_guts(self, data, last_build):
            return True
        # Walk the collected directories as check if they have been changed - which means files have been added or
        # removed. There is no need to check for the files, since `Tree` is only about the directory contents (which is
        # the list of files).
        stack = [data['root']]
        while stack:
            d = stack.pop()
            if misc.mtime(d) > last_build:
                logger.info("Building %s because directory %s changed", self.tocbasename, d)
                return True
            for nm in os.listdir(d):
                path = os.path.join(d, nm)
                if os.path.isdir(path):
                    stack.append(path)
        self[:] = data['data']  # collected files
        return False

    def _save_guts(self):
        # Use the attribute `data` to save the list
        self.data = self
        super()._save_guts()
        del self.data

    def assemble(self):
        logger.info("Building Tree %s", self.tocbasename)
        stack = [(self.root, self.prefix)]
        excludes = set()
        xexcludes = set()
        for name in self.excludes:
            if name.startswith('*'):
                xexcludes.add(name[1:])
            else:
                excludes.add(name)
        result = []
        while stack:
            dir, prefix = stack.pop()
            for filename in os.listdir(dir):
                if filename in excludes:
                    continue
                ext = os.path.splitext(filename)[1]
                if ext in xexcludes:
                    continue
                fullfilename = os.path.join(dir, filename)
                if prefix:
                    resfilename = os.path.join(prefix, filename)
                else:
                    resfilename = filename
                if os.path.isdir(fullfilename):
                    stack.append((fullfilename, resfilename))
                else:
                    result.append((resfilename, fullfilename, self.typecode))
        self[:] = result
