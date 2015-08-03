#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os

from PyInstaller import compat as compat
from PyInstaller.utils import misc
from PyInstaller.utils.misc import load_py_data_struct, save_py_data_struct
from .. import log as logging

logger = logging.getLogger(__name__)

def _check_guts_eq(attr, old, new, last_build):
    """
    rebuild is required if values differ
    """
    if old != new:
        logger.info("Building because %s changed", attr)
        return True
    return False


class TOC(compat.UserList):
    # TODO Simplify the representation and use directly Modulegraph objects.
    """
    TOC (Table of Contents) class is a list of tuples of the form (name, path, tytecode).

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
        compat.UserList.__init__(self)
        self.filenames = set()
        if initlist:
            for entry in initlist:
                self.append(entry)

    def _normentry(self, entry):
        if not isinstance(entry, tuple):
            logger.info("TOC found a %s, not a tuple", entry)
            raise TypeError("Expected tuple, not %s." % type(entry).__name__)
        name, path, typecode = entry
        if typecode in ["BINARY", "DATA"]:
            # Normalize the case for binary files and data files only (to avoid duplicates
            # for different cases under Windows). We can't do that for
            # Python files because the import semantic (even at runtime)
            # depends on the case.
            name = os.path.normcase(name)
        return (name, path, typecode)

    def append(self, entry):
        name, path, typecode = self._normentry(entry)
        if name not in self.filenames:
            self.data.append((name, path, typecode))
            self.filenames.add(name)

    def insert(self, pos, entry):
        name, path, typecode = self._normentry(entry)
        if name not in self.filenames:
            self.data.insert(pos, (name, path, typecode))
            self.filenames.add(name)

    def __add__(self, other):
        result = TOC(self)
        result.extend(other)
        return result

    def __radd__(self, other):
        result = TOC(other)
        result.extend(self)
        return result

    def extend(self, other):
        for entry in other:
            self.append(entry)

    def __sub__(self, other):
        other = TOC(other)
        filenames = self.filenames - other.filenames
        result = TOC()
        for name, path, typecode in self:
            if name in filenames:
                result.data.append((name, path, typecode))
        return result

    def __rsub__(self, other):
        result = TOC(other)
        return result.__sub__(self)

    def intersect(self, other):
        other = TOC(other)
        filenames = self.filenames.intersection(other.filenames)
        result = TOC()
        for name, path, typecode in other:
            if name in filenames:
                result.data.append((name, path, typecode))
        return result


class Target(object):
    invcnum = 0

    def __init__(self):
        from ..config import CONF
        # Get a (per class) unique number to avoid conflicts between
        # toc objects
        self.invcnum = self.__class__.invcnum
        self.__class__.invcnum += 1
        self.out = os.path.join(CONF['workpath'], 'out%02d-%s.toc' %
                                (self.invcnum, self.__class__.__name__))
        self.outnm = os.path.basename(self.out)
        self.dependencies = TOC()

    def __postinit__(self):
        logger.info("checking %s", self.__class__.__name__)
        if self.check_guts(misc.mtime(self.out)):
            self.assemble()

    GUTS = []

    def check_guts(self, last_build):
        pass

    def get_guts(self, last_build, missing='missing or bad'):
        """
        returns None if guts have changed
        """
        try:
            data = load_py_data_struct(self.out)
        except:
            logger.info("Building because %s %s", os.path.basename(self.out), missing)
            return None

        if len(data) != len(self.GUTS):
            logger.info("Building because %s is bad", self.outnm)
            return None
        for i, (attr, func) in enumerate(self.GUTS):
            if func is None:
                # no check for this value
                continue
            if func(attr, data[i], getattr(self, attr), last_build):
                return None
        return data


class Tree(Target, TOC):
    """
    This class is a way of creating a TOC (Table of Contents) that describes
    some or all of the files within a directory.
    """
    def __init__(self, root=None, prefix=None, excludes=None):
        """
        root
                The root of the tree (on the build system).
        prefix
                Optional prefix to the names of the target system.
        excludes
                A list of names to exclude. Two forms are allowed:

                    name
                        Files with this basename will be excluded (do not
                        include the path).
                    *.ext
                        Any file with the given extension will be excluded.
        """
        Target.__init__(self)
        TOC.__init__(self)
        self.root = root
        self.prefix = prefix
        self.excludes = excludes
        if excludes is None:
            self.excludes = []
        self.__postinit__()

    GUTS = (('root', _check_guts_eq),
            ('prefix', _check_guts_eq),
            ('excludes', _check_guts_eq),
            ('toc', None),
            )

    def check_guts(self, last_build):
        data = Target.get_guts(self, last_build)
        if not data:
            return True
        stack = [data[0]]  # root
        toc = data[3]  # toc
        while stack:
            d = stack.pop()
            if misc.mtime(d) > last_build:
                logger.info("Building %s because directory %s changed",
                            self.outnm, d)
                return True
            for nm in os.listdir(d):
                path = os.path.join(d, nm)
                if os.path.isdir(path):
                    stack.append(path)
        self.data = toc
        return False

    def assemble(self):
        logger.info("Building Tree %s", os.path.basename(self.out))
        stack = [(self.root, self.prefix)]
        excludes = {}
        xexcludes = {}
        for nm in self.excludes:
            if nm[0] == '*':
                xexcludes[nm[1:]] = 1
            else:
                excludes[nm] = 1
        rslt = []
        while stack:
            dir, prefix = stack.pop()
            for fnm in os.listdir(dir):
                if excludes.get(fnm, 0) == 0:
                    ext = os.path.splitext(fnm)[1]
                    if xexcludes.get(ext, 0) == 0:
                        fullfnm = os.path.join(dir, fnm)
                        rfnm = prefix and os.path.join(prefix, fnm) or fnm
                        if os.path.isdir(fullfnm):
                            stack.append((fullfnm, rfnm))
                        else:
                            rslt.append((rfnm, fullfnm, 'DATA'))
        self.data = rslt
        try:
            oldstuff = load_py_data_struct(self.out)
        except:
            oldstuff = None
        newstuff = (self.root, self.prefix, self.excludes, self.data)
        if oldstuff != newstuff:
            save_py_data_struct(self.out, newstuff)
            return 1
        logger.info("%s no change!", self.out)
        return 0


