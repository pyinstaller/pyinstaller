# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition to the permissions in the GNU General Public License, the
# authors give you unlimited permission to link or embed the compiled
# version of this file into combinations with other programs, and to
# distribute those combinations without any restriction coming from the
# use of this file. (The General Public License restrictions do apply in
# other respects; for example, they cover modification of the file, and
# distribution when not linked into a combine executable.)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

# subclasses may not need marshal or struct, but since they're
# builtin, importing is safe.
#
# While an Archive is really an abstraction for any "filesystem
# within a file", it is tuned for use with imputil.FuncImporter.
# This assumes it contains python code objects, indexed by the
# the internal name (ie, no '.py').
# See carchive.py for a more general archive (contains anything)
# that can be understood by a C program.

_verbose = 0
_listdir = None
_environ = None

### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.

import marshal
import struct
import imp
import sys


def debug(msg):
    if 0:
        sys.stderr.write(msg + "\n")


_c_suffixes = filter(lambda x: x[2] == imp.C_EXTENSION, imp.get_suffixes())

for nm in ('nt', 'posix'):
    if nm in sys.builtin_module_names:
        mod = __import__(nm)
        _listdir = mod.listdir
        _environ = mod.environ
        break

versuffix = '%d%d' % sys.version_info[:2]  # :todo: is this still used?

if "-vi" in sys.argv[1:]:
    _verbose = 1


class ArchiveReadError(RuntimeError):
    pass


class Archive:
    """
    A base class for a repository of python code objects.
    The extract method is used by imputil.ArchiveImporter
    to get code objects by name (fully qualified name), so
    an enduser "import a.b" would become
      extract('a.__init__')
      extract('a.b')
    """
    MAGIC = 'PYL\0'
    HDRLEN = 12  # default is MAGIC followed by python's magic, int pos of toc
    TOCPOS = 8
    TRLLEN = 0  # default - no trailer
    TOCTMPLT = {}
    os = None
    _bincache = None

    def __init__(self, path=None, start=0):
        """
        Initialize an Archive. If path is omitted, it will be an empty Archive.
        """
        self.toc = None
        self.path = path
        self.start = start
        import imp
        self.pymagic = imp.get_magic()
        if path is not None:
            self.lib = open(self.path, 'rb')
            self.checkmagic()
            self.loadtoc()

    ####### Sub-methods of __init__ - override as needed #############
    def checkmagic(self):
        """
        Overridable.
        Check to see if the file object self.lib actually has a file
        we understand.
        """
        self.lib.seek(self.start)  # default - magic is at start of file

        if self.lib.read(len(self.MAGIC)) != self.MAGIC:
            raise ArchiveReadError("%s is not a valid %s archive file"
                                   % (self.path, self.__class__.__name__))

        if self.lib.read(len(self.pymagic)) != self.pymagic:
            raise ArchiveReadError("%s has version mismatch to dll" %
                (self.path))

        self.lib.read(4)

    def loadtoc(self):
        """
        Overridable.
        Default: After magic comes an int (4 byte native) giving the
        position of the TOC within self.lib.
        Default: The TOC is a marshal-able string.
        """
        self.lib.seek(self.start + self.TOCPOS)
        (offset,) = struct.unpack('!i', self.lib.read(4))
        self.lib.seek(self.start + offset)
        self.toc = marshal.load(self.lib)

    ######## This is what is called by FuncImporter #######
    ## Since an Archive is flat, we ignore parent and modname.
    #XXX obsolete - imputil only code
    ##  def get_code(self, parent, modname, fqname):
    ##      pass

    ####### Core method - Override as needed  #########
    def extract(self, name):
        """
        Get the object corresponding to name, or None.
        For use with imputil ArchiveImporter, object is a python code object.
        'name' is the name as specified in an 'import name'.
        'import a.b' will become:
        extract('a') (return None because 'a' is not a code object)
        extract('a.__init__') (return a code object)
        extract('a.b') (return a code object)
        Default implementation:
          self.toc is a dict
          self.toc[name] is pos
          self.lib has the code object marshal-ed at pos
        """
        ispkg, pos = self.toc.get(name, (0, None))
        if pos is None:
            return None
        self.lib.seek(self.start + pos)
        return ispkg, marshal.load(self.lib)

    ########################################################################
    # Informational methods

    def contents(self):
        """
        Return a list of the contents
        Default implementation assumes self.toc is a dict like object.
        Not required by ArchiveImporter.
        """
        return self.toc.keys()

    ########################################################################
    # Building

    ####### Top level method - shouldn't need overriding #######
    def build(self, path, lTOC):
        """
        Create an archive file of name 'path'.
        lTOC is a 'logical TOC' - a list of (name, path, ...)
        where name is the internal name, eg 'a'
        and path is a file to get the object from, eg './a.pyc'.
        """
        self.path = path
        self.lib = open(path, 'wb')
        #reserve space for the header
        if self.HDRLEN:
            self.lib.write('\0' * self.HDRLEN)

            #create an empty toc

        if type(self.TOCTMPLT) == type({}):
            self.toc = {}
        else:       # assume callable
            self.toc = self.TOCTMPLT()

        for tocentry in lTOC:
            self.add(tocentry)   # the guts of the archive

        tocpos = self.lib.tell()
        self.save_toc(tocpos)
        if self.TRLLEN:
            self.save_trailer(tocpos)
        if self.HDRLEN:
            self.update_headers(tocpos)
        self.lib.close()

    ####### manages keeping the internal TOC and the guts in sync #######
    def add(self, entry):
        """
        Override this to influence the mechanics of the Archive.
        Assumes entry is a seq beginning with (nm, pth, ...) where
        nm is the key by which we'll be asked for the object.
        pth is the name of where we find the object. Overrides of
        get_obj_from can make use of further elements in entry.
        """
        if self.os is None:
            import os
            self.os = os
        nm = entry[0]
        pth = entry[1]
        pynm, ext = self.os.path.splitext(self.os.path.basename(pth))
        ispkg = pynm == '__init__'
        assert ext in ('.pyc', '.pyo')
        self.toc[nm] = (ispkg, self.lib.tell())
        f = open(entry[1], 'rb')
        f.seek(8)  # skip magic and timestamp
        self.lib.write(f.read())

    def save_toc(self, tocpos):
        """
        Default - toc is a dict
        Gets marshaled to self.lib
        """
        marshal.dump(self.toc, self.lib)

    def save_trailer(self, tocpos):
        """
        Default - not used
        """
        pass

    def update_headers(self, tocpos):
        """
        Default - MAGIC + Python's magic + tocpos
        """
        self.lib.seek(self.start)
        self.lib.write(self.MAGIC)
        self.lib.write(self.pymagic)
        self.lib.write(struct.pack('!i', tocpos))


class DummyZlib:
    def decompress(self, data):
        #raise RuntimeError, "zlib required but cannot be imported"
        return data

    def compress(self, data, lvl):
        #raise RuntimeError, "zlib required but cannot be imported"
        return data


# Used by PYZOwner
import iu


class ZlibArchive(Archive):
    """
    ZlibArchive - an archive with compressed entries. Archive is read
    from the executable created by PyInstaller.
    """
    MAGIC = 'PYZ\0'
    TOCPOS = 8
    HDRLEN = Archive.HDRLEN + 5
    TRLLEN = 0
    TOCTMPLT = {}
    LEVEL = 9

    def __init__(self, path=None, offset=None, level=9, crypt=None):
        if path is None:
            offset = 0
        elif offset is None:
            for i in range(len(path) - 1, - 1, - 1):
                if path[i] == '?':
                    try:
                        offset = int(path[i + 1:])
                    except ValueError:
                        # Just ignore any spurious "?" in the path
                        # (like in Windows UNC \\?\<path>).
                        continue
                    path = path[:i]
                    break
            else:
                offset = 0

        self.LEVEL = level
        if crypt is not None:
            self.crypted = 1
            self.key = (crypt + "*" * 32)[:32]
        else:
            self.crypted = 0
            self.key = None

        Archive.__init__(self, path, offset)

        # dynamic import so not imported if not needed
        global zlib
        if self.LEVEL:
            try:
                import zlib
            except ImportError:
                zlib = DummyZlib()
        else:
            print "WARNING: compression level=0!!!"
            zlib = DummyZlib()

        global AES
        if self.crypted:
            import AES

    def _iv(self, nm):
        IV = nm * ((AES.block_size + len(nm) - 1) // len(nm))
        return IV[:AES.block_size]

    def extract(self, name):
        (ispkg, pos, lngth) = self.toc.get(name, (0, None, 0))
        if pos is None:
            return None
        self.lib.seek(self.start + pos)
        obj = self.lib.read(lngth)
        if self.crypted:
            if self.key is None:
                raise ImportError('decryption key not found')
            obj = AES.new(self.key, AES.MODE_CFB, self._iv(name)).decrypt(obj)
        try:
            obj = zlib.decompress(obj)
        except zlib.error:
            if not self.crypted:
                raise
            raise ImportError('invalid decryption key')
        try:
            co = marshal.loads(obj)
        except EOFError:
            raise ImportError("PYZ entry '%s' failed to unmarshal" % name)
        return ispkg, co

    def add(self, entry):
        if self.os is None:
            import os
            self.os = os
        nm = entry[0]
        pth = entry[1]
        base, ext = self.os.path.splitext(self.os.path.basename(pth))
        ispkg = base == '__init__'
        try:
            txt = open(pth[:-1], 'rU').read() + '\n'
        except (IOError, OSError):
            try:
                f = open(pth, 'rb')
                f.seek(8)  # skip magic and timestamp
                bytecode = f.read()
                marshal.loads(bytecode).co_filename  # to make sure it's valid
                obj = zlib.compress(bytecode, self.LEVEL)
            except (IOError, ValueError, EOFError, AttributeError):
                raise ValueError("bad bytecode in %s and no source" % pth)
        else:
            txt = txt.replace('\r\n', '\n')
            try:
                import os
                co = compile(txt, self.os.path.join(self.path, nm), 'exec')
            except SyntaxError, e:
                print "Syntax error in", pth[:-1]
                print e.args
                raise
            obj = zlib.compress(marshal.dumps(co), self.LEVEL)
        if self.crypted:
            obj = AES.new(self.key, AES.MODE_CFB, self._iv(nm)).encrypt(obj)
        self.toc[nm] = (ispkg, self.lib.tell(), len(obj))
        self.lib.write(obj)

    def update_headers(self, tocpos):
        """
        add level
        """
        Archive.update_headers(self, tocpos)
        self.lib.write(struct.pack('!iB', self.LEVEL, self.crypted))

    def checkmagic(self):
        Archive.checkmagic(self)
        self.LEVEL, self.crypted = struct.unpack('!iB', self.lib.read(5))


class Keyfile:
    def __init__(self, fn=None):
        if fn is None:
            fn = sys.argv[0]
            if fn[-4] == '.':
                fn = fn[:-4]
            fn += ".key"

        execfile(fn, {"__builtins__": None}, self.__dict__)
        if not hasattr(self, "key"):
            self.key = None


class PYZOwner(iu.Owner):
    """
    Load bytecode of Python modules from the executable created by PyInstaller.

    Python bytecode is zipped and appended to the executable.
    """
    def __init__(self, path):
        try:
            # Unzip zip archive bundled with the executable.
            self.pyz = ZlibArchive(path)
            self.pyz.checkmagic()
        except (IOError, ArchiveReadError), e:
            raise iu.OwnerError(e)
        if self.pyz.crypted:
            if not hasattr(sys, "keyfile"):
                sys.keyfile = Keyfile()
            self.pyz = ZlibArchive(path, crypt=sys.keyfile.key)
        iu.Owner.__init__(self, path)

    def getmod(self, nm, newmod=imp.new_module):
        rslt = self.pyz.extract(nm)
        if rslt is None:
            return None
        ispkg, bytecode = rslt
        mod = newmod(nm)

        # Replace bytecode.co_filename by something more meaningful:
        # e.g. /absolute/path/frozen_executable?12345/os/path.pyc
        # Paths from developer machine are masked.
        try:
            # Python packages points to files  __init__.pyc.
            if ispkg:
                mod.__file__ = iu._os_path_join(iu._os_path_join(self.path,
                    nm.replace('.', iu._os_sep)), '__init__.pyc')
            else:
                mod.__file__ = iu._os_path_join(self.path,
                    nm.replace('.', iu._os_sep) + '.pyc')
        except AttributeError:
            raise ImportError("PYZ entry '%s' (%s) is not a valid code object"
                % (nm, repr(bytecode)))

        # Python has modules and packages. A Python package is container
        # for several modules or packages.
        if ispkg:

            if '_MEIPASS2' in _environ:
                localpath = _environ['_MEIPASS2'][:-1]
            else:
                localpath = iu._os_path_dirname(self.path)

            # A python packages has to have __path__ attribute.
            mod.__path__ = [iu._os_path_dirname(mod.__file__), self.path, localpath,
                ]

            debug("PYZOwner setting %s's __path__: %s" % (nm, mod.__path__))

            importer = iu.PathImportDirector(mod.__path__,
                {self.path: PkgInPYZImporter(nm, self),
                localpath: ExtInPkgImporter(localpath, nm)},
                [iu.DirOwner])
            mod.__importsub__ = importer.getmod

        mod.__co__ = bytecode
        return mod


class PkgInPYZImporter:
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner

    def getmod(self, nm):
        debug("PkgInPYZImporter.getmod %s -> %s" % (nm, self.name + '.' + nm))
        return self.owner.getmod(self.name + '.' + nm)


class ExtInPkgImporter(iu.DirOwner):
    def __init__(self, path, prefix):
        iu.DirOwner.__init__(self, path)
        self.prefix = prefix

    def getmod(self, nm):
        return iu.DirOwner.getmod(self, self.prefix + '.' + nm)
