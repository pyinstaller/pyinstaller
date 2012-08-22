#
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


# Subclasses may not need marshal or struct, but since they're
# builtin, importing is safe.
#
# While an Archive is really an abstraction for any "filesystem
# within a file", it is tuned for use with imputil.FuncImporter.
# This assumes it contains python code objects, indexed by the
# the internal name (ie, no '.py').
#
# See pyi_carchive.py for a more general archive (contains anything)
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
        sys.stderr.flush()


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


class Archive(object):
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

    def _start_add_entries(self, path):
        """
        Open an empty archive for addition of entries.
        """
        assert(self.path is None)

        self.path = path
        self.lib = open(path, 'wb')
        # Reserve space for the header.
        if self.HDRLEN:
            self.lib.write('\0' * self.HDRLEN)

        # Create an empty table of contents.
        if type(self.TOCTMPLT) == type({}):
            self.toc = {}
        else:
            # FIXME Why do we need to assume callables and
            # why not use @property decorator.
            self.toc = self.TOCTMPLT()  # Assume callable.

    def _add_from_table_of_contents(self, toc):
        """
        Add entries from a logical TOC (without absolute positioning info).
        An entry is an entry in a logical TOC is a tuple,
          entry[0] is name (under which it will be saved).
          entry[1] is fullpathname of the file.
          entry[2] is a flag for it's storage format (True or 1 if compressed)
          entry[3] is the entry's type code.
        """
        for toc_entry in toc:
            self.add(toc_entry)  # The guts of the archive.

    def _finalize(self):
        """
        Finalize an archive which has been opened using _start_add_entries(),
        writing any needed padding and the table of contents.
        """
        toc_pos = self.lib.tell()
        self.save_toc(toc_pos)
        if self.TRLLEN:
            self.save_trailer(toc_pos)
        if self.HDRLEN:
            self.update_headers(toc_pos)
        self.lib.close()

    def build(self, archive_path, logical_toc):
        """
        Create an archive file of name 'archive_path'.
        logical_toc is a 'logical TOC' - a list of (name, path, ...)
        where name is the internal name, eg 'a'
        and path is a file to get the object from, eg './a.pyc'.
        """
        self._start_add_entries(archive_path)
        self._add_from_table_of_contents(logical_toc)
        self._finalize()

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


# Used by PYZOwner
import pyi_iu


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
    NO_COMPRESSION_LEVEL = 0

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

        # Zlib compression level.
        self.LEVEL = level
        if crypt is not None:
            self.crypted = 1
            self.key = (crypt + "*" * 32)[:32]
        else:
            self.crypted = 0
            self.key = None

        Archive.__init__(self, path, offset)

        # dynamic import so not imported if not needed
        self._mod_zlib = None
        self._mod_aes = None

        if self.LEVEL > self.NO_COMPRESSION_LEVEL:
            try:
                self._mod_zlib = __import__('zlib')
            except ImportError:
                raise RuntimeError('zlib required but cannot be imported')

        # FIXME Cryptography is broken in PyInstaller.
        if self.crypted:
            self._mod_aes = __import__('AES')

    def _iv(self, nm):
        IV = nm * ((self._mod_aes.block_size + len(nm) - 1) // len(nm))
        return IV[:self._mod_aes.block_size]

    def extract(self, name):
        (ispkg, pos, lngth) = self.toc.get(name, (0, None, 0))
        if pos is None:
            return None
        self.lib.seek(self.start + pos)
        obj = self.lib.read(lngth)
        if self.crypted:
            if self.key is None:
                raise ImportError('decryption key not found')
            obj = self._mod_aes.new(self.key, self._mod_aes.MODE_CFB, self._iv(name)).decrypt(obj)
        try:
            obj = self._mod_zlib.decompress(obj)
        except self._mod_zlib.error:
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
                obj = self._mod_zlib.compress(bytecode, self.LEVEL)
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
            obj = self._mod_zlib.compress(marshal.dumps(co), self.LEVEL)
        if self.crypted:
            obj = self._mod_aes.new(self.key, self._mod_aes.MODE_CFB, self._iv(nm)).encrypt(obj)
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


class Keyfile(object):
    def __init__(self, fn=None):
        if fn is None:
            fn = sys.argv[0]
            if fn[-4] == '.':
                fn = fn[:-4]
            fn += ".key"

        execfile(fn, {"__builtins__": None}, self.__dict__)
        if not hasattr(self, "key"):
            self.key = None


class PYZOwner(pyi_iu.Owner):
    """
    Load bytecode of Python modules from the executable created by PyInstaller.

    Python bytecode is zipped and appended to the executable.

    NOTE: PYZ format cannot be replaced by zipimport module.

    The problem is that we have no control over zipimport; for instance,
    it doesn't work if the zip file is embedded into a PKG appended
    to an executable, like we create in one-file.
    """
    def __init__(self, path):
        try:
            # Unzip zip archive bundled with the executable.
            self.pyz = ZlibArchive(path)
            self.pyz.checkmagic()
        except (IOError, ArchiveReadError), e:
            raise pyi_iu.OwnerError(e)
        if self.pyz.crypted:
            if not hasattr(sys, "keyfile"):
                sys.keyfile = Keyfile()
            self.pyz = ZlibArchive(path, crypt=sys.keyfile.key)
        pyi_iu.Owner.__init__(self, path)

    def getmod(self, nm, newmod=imp.new_module):
        rslt = self.pyz.extract(nm)
        if rslt is None:
            return None
        ispkg, bytecode = rslt
        mod = newmod(nm)

        # Replace bytecode.co_filename by something more meaningful:
        # e.g. /absolute/path/frozen_executable/path/to/module/module_name.pyc
        # Paths from developer machine are masked.
        try:
            # Set __file__ attribute of a module relative to the executable
            # so that data files can be found. The absolute absolute path
            # to the executable is taken from sys.prefix. In onefile mode it
            # points to the temp directory where files are unpacked by PyInstaller.
            abspath = sys.prefix
            # Then, append the appropriate suffix (__init__.pyc for a package, or just .pyc for a module).
            if ispkg:
                mod.__file__ = pyi_iu._os_path_join(pyi_iu._os_path_join(abspath,
                    nm.replace('.', pyi_iu._os_sep)), '__init__.pyc')
            else:
                mod.__file__ = pyi_iu._os_path_join(abspath,
                    nm.replace('.', pyi_iu._os_sep) + '.pyc')
        except AttributeError:
            raise ImportError("PYZ entry '%s' (%s) is not a valid code object"
                % (nm, repr(bytecode)))

        # Python has modules and packages. A Python package is container
        # for several modules or packages.
        if ispkg:
            # Since PYTHONHOME is set in bootloader, 'sys.prefix' points to the
            # correct path where PyInstaller should find bundled dynamic
            # libraries. In one-file mode it points to the tmp directory where
            # bundled files are extracted at execution time.
            localpath = sys.prefix

            # A python packages has to have __path__ attribute.
            mod.__path__ = [pyi_iu._os_path_dirname(mod.__file__), self.path, localpath,
                ]

            debug("PYZOwner setting %s's __path__: %s" % (nm, mod.__path__))

            importer = pyi_iu.PathImportDirector(mod.__path__,
                {self.path: PkgInPYZImporter(nm, self),
                localpath: ExtInPkgImporter(localpath, nm)},
                [pyi_iu.DirOwner])
            mod.__importsub__ = importer.getmod

        mod.__co__ = bytecode
        return mod


class PkgInPYZImporter(object):
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner

    def getmod(self, nm):
        debug("PkgInPYZImporter.getmod %s -> %s" % (nm, self.name + '.' + nm))
        return self.owner.getmod(self.name + '.' + nm)


class ExtInPkgImporter(pyi_iu.DirOwner):
    def __init__(self, path, prefix):
        pyi_iu.DirOwner.__init__(self, path)
        self.prefix = prefix

    def getmod(self, nm):
        return pyi_iu.DirOwner.getmod(self, self.prefix + '.' + nm)
