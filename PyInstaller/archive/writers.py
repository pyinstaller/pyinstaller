#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Utilities to create data structures for embedding Python modules and additional
files into the executable.
"""

# TODO clean up this module

# TODO copied from pyimod02_carchive

# While an Archive is really an abstraction for any "filesystem
# within a file", it is tuned for use with imputil.FuncImporter.
# This assumes it contains python code objects, indexed by the
# the internal name (ie, no '.py').
#
# See pyi_carchive.py for a more general archive (contains anything)
# that can be understood by a C program.

import os
import sys
from types import CodeType
import marshal
import zlib

from .readers import CArchiveReader, PYZ_TYPE_MODULE, PYZ_TYPE_PKG, PYZ_TYPE_DATA
from ..compat import BYTECODE_MAGIC


class ArchiveFile(object):
    """
    File class support auto open when access member from file object
    This class is use to avoid file locking on windows
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pos = 0
        self.fd = None
        self.__open()

    def __getattr__(self, name):
        """
        Auto open file when access member from file object
        This function only call when member of name not exist in self
        """
        assert self.fd
        return getattr(self.fd, name)

    def __open(self):
        """
        Open file and seek to pos record from last close
        """
        if self.fd is None:
            self.fd = open(*self.args, **self.kwargs)
            self.fd.seek(self.pos)

    def __enter__(self):
        self.__open()

    def __exit__(self, type, value, traceback):
        assert self.fd
        self.close()

    def close(self):
        """
        Close file and record pos
        """
        if self.fd is not None:
            self.pos = self.fd.tell()
            self.fd.close()
            self.fd = None


class ArchiveReadError(RuntimeError):
    pass


class ArchiveWriter(object):
    """
    A base class for a repository of python code objects.
    The extract method is used by imputil.ArchiveImporter
    to get code objects by name (fully qualified name), so
    an enduser "import a.b" would become
      extract('a.__init__')
      extract('a.b')
    """
    MAGIC = b'PYL\0'
    HDRLEN = 12  # default is MAGIC followed by python's magic, int pos of toc
    TOCPOS = 8
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

        if path is not None:
            self.lib = ArchiveFile(self.path, 'rb')
            with self.lib:
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

        if self.lib.read(len(BYTECODE_MAGIC)) != BYTECODE_MAGIC:
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
        # use marshal.loads() since load() arg must be a file object
        self.toc = marshal.loads(self.lib.read())

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
        with self.lib:
            self.lib.seek(self.start + pos)
            # use marshal.loads() sind load() arg must be a file object
            obj = marshal.loads(self.lib.read())
        return ispkg, obj

    ########################################################################
    # Informational methods

    def contents(self):
        """
        Return a list of the contents
        Default implementation assumes self.toc is a dict like object.
        Not required by ArchiveImporter.
        """
        return list(self.toc.keys())

    ########################################################################
    # Building

    ####### Top level method - shouldn't need overriding #######

    def _start_add_entries(self, path):
        """
        Open an empty archive for addition of entries.
        """
        assert(self.path is None)

        self.path = path
        self.lib = ArchiveFile(path, 'wb')
        # Reserve space for the header.
        if self.HDRLEN:
            self.lib.write(b'\0' * self.HDRLEN)

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
        nm = entry[0]
        pth = entry[1]
        pynm, ext = os.path.splitext(os.path.basename(pth))
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
        try:
            self.lib.write(marshal.dumps(self.toc))
        # If the TOC to be marshalled contains an unmarshallable object, Python
        # raises a cryptic exception providing no details on why such object is
        # unmarshallable. Correct this by iteratively inspecting the TOC for
        # unmarshallable objects.
        except ValueError as exception:
            if str(exception) == 'unmarshallable object':

                # List of all marshallable types.
                MARSHALLABLE_TYPES = set((
                    bool, int, float, complex, str, bytes, bytearray,
                    tuple, list, set, frozenset, dict, CodeType))
                if sys.version_info[0] == 2:
                    MARSHALLABLE_TYPES.add(long)

                for module_name, module_tuple in self.toc.items():
                    if type(module_name) not in MARSHALLABLE_TYPES:
                        print('Module name "%s" (%s) unmarshallable.' % (module_name, type(module_name)))
                    if type(module_tuple) not in MARSHALLABLE_TYPES:
                        print('Module "%s" tuple "%s" (%s) unmarshallable.' % (module_name, module_tuple, type(module_tuple)))
                    elif type(module_tuple) == tuple:
                        for i in range(len(module_tuple)):
                            if type(module_tuple[i]) not in MARSHALLABLE_TYPES:
                                print('Module "%s" tuple index %s item "%s" (%s) unmarshallable.' % (module_name, i, module_tuple[i], type(module_tuple[i])))

            raise

    def update_headers(self, tocpos):
        """
        Default - MAGIC + Python's magic + tocpos
        """
        self.lib.seek(self.start)
        self.lib.write(self.MAGIC)
        self.lib.write(BYTECODE_MAGIC)
        self.lib.write(struct.pack('!i', tocpos))


class ZlibArchiveWriter(ArchiveWriter):
    """
    ZlibArchive - an archive with compressed entries. Archive is read
    from the executable created by PyInstaller.

    This archive is used for bundling python modules inside the executable.

    NOTE: The whole ZlibArchive (PYZ) is compressed so it is not necessary
          to compress single modules with zlib.
    """
    MAGIC = b'PYZ\0'
    TOCPOS = 8
    HDRLEN = ArchiveWriter.HDRLEN + 5
    TOCTMPLT = {}
    COMPRESSION_LEVEL = 6  # Default level of the 'zlib' module from Python.

    def __init__(self, path=None, offset=None, code_dict={},
                 cipher=None):
        """
        code_dict      dict containing module code objects from ModuleGraph.
        """
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

        # Keep references to module code objects constructed by ModuleGraph
        # to avoid writting .pyc/pyo files to hdd.
        self.code_dict = code_dict

        super(ZlibArchiveWriter, self).__init__(path, offset)

        if cipher:
            self.crypted = 1
            self.cipher = cipher
        else:
            self.crypted = 0

    def add(self, entry):
        name, path, typ = entry
        if typ == 'PYMODULE':
            typ = PYZ_TYPE_MODULE
            if path in ('-', None):
                # This is a NamespacePackage, modulegraph marks them
                # by using the filename '-'. (But wants to use None,
                # so check for None, too, to be forward-compatible.)
                typ = PYZ_TYPE_PKG
            else:
                base, ext = os.path.splitext(os.path.basename(path))
                if base == '__init__':
                    typ = PYZ_TYPE_PKG
            data = marshal.dumps(self.code_dict[name])
        else:
            typ = PYZ_TYPE_DATA
            with open(path, 'rb') as fh:
                data = fh.read()
            # Use forward slash as path-separator in PYZ (like in zipfiles)
            if os.path.altsep:
                name = name.replace(os.path.altsep, os.path.sep)
            name = name.replace(os.path.sep, '/')

        obj = zlib.compress(data, self.COMPRESSION_LEVEL)

        # First compress then encrypt.
        if self.crypted:
            obj = self.cipher.encrypt(obj)

        self.toc[name] = (typ, self.lib.tell(), len(obj))
        self.lib.write(obj)

    def update_headers(self, tocpos):
        """
        add level
        """
        ArchiveWriter.update_headers(self, tocpos)
        self.lib.write(struct.pack('!B', self.crypted))


# TODO copied from pyimod03_carchive


import struct
import sys



class NotAnArchiveError(Exception):
    pass


class CTOCWriter(object):
    """
    A class encapsulating the table of contents of a CArchive.

    When written to disk, it is easily read from C.
    """
    ENTRYSTRUCT = '!iiiiBB'  # (structlen, dpos, dlen, ulen, flag, typcd) followed by name
    ENTRYLEN = struct.calcsize(ENTRYSTRUCT)

    def __init__(self):
        self.data = []

    def tobinary(self):
        """
        Return self as a binary string.
        """
        rslt = []
        for (dpos, dlen, ulen, flag, typcd, nm) in self.data:
            # Encode all names using UTF-8. This should be save as
            # standard python modules only contain ascii-characters
            # (and standard shared libraries should have the same) and
            # thus the C-code still can handle this correctly.
            nm = nm.encode('utf-8')
            nmlen = len(nm) + 1       # add 1 for a '\0'
            # align to 16 byte boundary so xplatform C can read
            toclen = nmlen + self.ENTRYLEN
            if toclen % 16 == 0:
                pad = b'\0'
            else:
                padlen = 16 - (toclen % 16)
                pad = b'\0' * padlen
                nmlen = nmlen + padlen
            rslt.append(struct.pack(self.ENTRYSTRUCT + '%is' % nmlen,
                                    nmlen + self.ENTRYLEN, dpos, dlen, ulen,
                                    flag, ord(typcd), nm + pad))

        return b''.join(rslt)

    def add(self, dpos, dlen, ulen, flag, typcd, nm):
        """
        Add an entry to the table of contents.

        DPOS is data position.
        DLEN is data length.
        ULEN is the uncompressed data len.
        FLAG says if the data is compressed.
        TYPCD is the "type" of the entry (used by the C code)
        NM is the entry's name.

        This function is used only while creating an executable.
        """
        # Ensure forward slashes in paths are on Windows converted to back
        # slashes '\\' since on Windows the bootloader works only with back
        # slashes.
        nm = os.path.normpath(nm)
        self.data.append((dpos, dlen, ulen, flag, typcd, nm))

    def get(self, ndx):
        """
        Return the table of contents entry (tuple) at index NDX.
        """
        return self.data[ndx]

    def __getitem__(self, ndx):
        return self.data[ndx]

    def find(self, name):
        """
        Return the index of the toc entry with name NAME.

        Return -1 for failure.
        """
        for i, nm in enumerate(self.data):
            if nm[-1] == name:
                return i
        return -1


class CArchiveWriter(ArchiveWriter):
    """
    An Archive subclass that can hold arbitrary data.

    This class encapsulates all files that are bundled within an executable.
    It can contain ZlibArchive (Python .pyc files), dlls, Python C extensions
    and all other data files that are bundled in --onefile mode.

    Easily handled from C or from Python.
    """
    # MAGIC is usefull to verify that conversion of Python data types
    # to C structure and back works properly.
    MAGIC = b'MEI\014\013\012\013\016'
    HDRLEN = 0
    TOCTMPLT = CTOCWriter
    LEVEL = 9

    # Cookie - holds some information for the bootloader. C struct format
    # definition. '!' at the beginning means network byte order.
    # C struct looks like:
    #
    #   typedef struct _cookie {
    #       char magic[8]; /* 'MEI\014\013\012\013\016' */
    #       int  len;      /* len of entire package */
    #       int  TOC;      /* pos (rel to start) of TableOfContents */
    #       int  TOClen;   /* length of TableOfContents */
    #       int  pyvers;   /* new in v4 */
    #       char pylibname[64];    /* Filename of Python dynamic library. */
    #   } COOKIE;
    #
    _cookie_format = '!8siiii64s'
    _cookie_size = struct.calcsize(_cookie_format)

    def __init__(self, archive_path=None, start=0, length=0, pylib_name=''):
        """
        Constructor.

        archive_path path name of file (create empty CArchive if path is None).
        start        is the seekposition within PATH.
        len          is the length of the CArchive (if 0, then read till EOF).
        pylib_name   name of Python DLL which bootloader will use.
        """
        self.length = length
        self._pylib_name = pylib_name

        # A CArchive created from scratch starts at 0, no leading bootloader.
        self.pkg_start = 0
        super(CArchiveWriter, self).__init__(archive_path, start)

    def _finalize(self):
        """
        Finalize an archive which has been opened using _start_add_entries(),
        writing any needed padding and the table of contents.

        Overrides parent method because we need to save cookie and headers.
        """
        toc_pos = self.lib.tell() - self.pkg_start
        self.save_toc(toc_pos)
        self.save_cookie(toc_pos)

        if self.HDRLEN:
            self.update_headers(toc_pos)

        self.lib.close()

    def contents(self):
        """
        Return the names of the entries.
        """
        rslt = []
        for (dpos, dlen, ulen, flag, typcd, nm) in self.toc:
            rslt.append(nm)
        return rslt

    def add(self, entry):
        """
        Add an ENTRY to the CArchive.

        ENTRY must have:
          entry[0] is name (under which it will be saved).
          entry[1] is fullpathname of the file.
          entry[2] is a flag for it's storage format (0==uncompressed,
          1==compressed)
          entry[3] is the entry's type code.
          Version 5:
            If the type code is 'o':
              entry[0] is the runtime option
              eg: v  (meaning verbose imports)
                  u  (menaing unbuffered)
                  W arg (warning option arg)
                  s  (meaning do site.py processing.
        """
        (nm, pathnm, flag, typcd) = entry[:4]
        # FIXME Could we make the version 5 the default one?
        # Version 5 - allow type 'o' = runtime option.
        try:
            if typcd in ('o', 'd'):
                fh = None
                ulen = 0
                postfix = b''
                flag = 0
            elif typcd == 's':
                # If it's a source code file, add \0 terminator as it will be
                # executed as-is by the bootloader.
                # Must read this in binary-mode, too, because
                # compression only accepts a binary stream. Further we
                # do not process it here, so why decode?
                fh = open(pathnm, 'rb')
                postfix = b'\n\0'
                ulen = os.fstat(fh.fileno()).st_size + len(postfix)
            else:
                fh = open(pathnm, 'rb')
                postfix = b''
                ulen = os.fstat(fh.fileno()).st_size
        except IOError:
            print("Cannot find ('%s', '%s', %s, '%s')" % (nm, pathnm, flag, typcd))
            raise

        where = self.lib.tell()
        assert flag in range(3)
        if not fh:
            # no need to write anything
            pass
        elif flag == 1:
            assert fh
            comprobj = zlib.compressobj(self.LEVEL)
            while 1:
                buf = fh.read(16*1024)
                if not buf:
                    break
                self.lib.write(comprobj.compress(buf))
            self.lib.write(comprobj.compress(postfix))
            self.lib.write(comprobj.flush())
        else:
            assert fh
            while 1:
                buf = fh.read(16*1024)
                if not buf:
                    break
                self.lib.write(buf)
            self.lib.write(postfix)

        dlen = self.lib.tell() - where
        if typcd == 'm':
            if pathnm.find('.__init__.py') > -1:
                typcd = 'M'

        self.toc.add(where, dlen, ulen, flag, typcd, nm)


    def save_toc(self, tocpos):
        """
        Save the table of contents to disk.
        """
        self.tocpos = tocpos
        tocstr = self.toc.tobinary()
        self.toclen = len(tocstr)
        self.lib.write(tocstr)

    def save_cookie(self, tocpos):
        """
        Save the cookie for the bootlader to disk.

        CArchives can be opened from the end - the cookie points
        back to the start.
        """
        totallen = tocpos + self.toclen + self._cookie_size
        pyvers = sys.version_info[0] * 10 + sys.version_info[1]
        # Before saving cookie we need to convert it to corresponding
        # C representation.
        cookie = struct.pack(self._cookie_format, self.MAGIC, totallen,
                tocpos, self.toclen, pyvers, self._pylib_name.encode('ascii'))
        self.lib.write(cookie)

    def openEmbedded(self, name):
        """
        Open a CArchive of name NAME embedded within this CArchive.

        This fuction is used by archive_viewer.py utility.
        """
        ndx = self.toc.find(name)

        if ndx == -1:
            raise KeyError("Member '%s' not found in %s" % (name, self.path))
        (dpos, dlen, ulen, flag, typcd, nm) = self.toc.get(ndx)

        if typcd not in "zZ":
            raise NotAnArchiveError('%s is not an archive' % name)

        if flag:
            raise ValueError('Cannot open compressed archive %s in place' %
                    name)
        return CArchiveReader(self.path, self.pkg_start + dpos, dlen)
