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


"""
Utilities to create data structures for embedding Python modules and additional
files into the executable.
"""

# While an Archive is really an abstraction for any "filesystem
# within a file", it is tuned for use with imputil.FuncImporter.
# This assumes it contains python code objects, indexed by the
# the internal name (ie, no '.py').
#
# See pyi_carchive.py for a more general archive (contains anything)
# that can be understood by a C program.

import os
import sys
import struct
from types import CodeType
import marshal
import zlib
import io

from PyInstaller.building.utils import get_code_object, strip_paths_in_code,\
    fake_pyc_timestamp
from PyInstaller.loader.pyimod02_archive import PYZ_TYPE_MODULE, PYZ_TYPE_PKG, \
    PYZ_TYPE_DATA, PYZ_TYPE_NSPKG
from ..compat import BYTECODE_MAGIC, is_py37, is_win


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

    def __init__(self, archive_path, logical_toc):
        """
        Create an archive file of name 'archive_path'.
        logical_toc is a 'logical TOC' - a list of (name, path, ...)
        where name is the internal name, eg 'a'
        and path is a file to get the object from, eg './a.pyc'.
        """
        self.start = 0

        self._start_add_entries(archive_path)
        self._add_from_table_of_contents(logical_toc)
        self._finalize()

    def _start_add_entries(self, archive_path):
        """
        Open an empty archive for addition of entries.
        """
        self.lib = open(archive_path, 'wb')
        # Reserve space for the header.
        if self.HDRLEN:
            self.lib.write(b'\0' * self.HDRLEN)
        # Create an empty table of contents.
        # Use a list to support reproducible builds
        self.toc = []

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
        self.save_trailer(toc_pos)
        if self.HDRLEN:
            self.update_headers(toc_pos)
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
        nm = entry[0]
        pth = entry[1]
        pynm, ext = os.path.splitext(os.path.basename(pth))
        ispkg = pynm == '__init__'
        assert ext in ('.pyc', '.pyo')
        self.toc.append((nm, (ispkg, self.lib.tell())))
        with open(entry[1], 'rb') as f:
            f.seek(8)  # skip magic and timestamp
            self.lib.write(f.read())

    def save_trailer(self, tocpos):
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
                MARSHALLABLE_TYPES = {
                    bool, int, float, complex, str, bytes, bytearray, tuple,
                    list, set, frozenset, dict, CodeType
                }

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
    COMPRESSION_LEVEL = 6  # Default level of the 'zlib' module from Python.

    def __init__(self, archive_path, logical_toc, code_dict=None, cipher=None):
        """
        code_dict      dict containing module code objects from ModuleGraph.
        """
        # Keep references to module code objects constructed by ModuleGraph
        # to avoid writting .pyc/pyo files to hdd.
        self.code_dict = code_dict or {}
        self.cipher = cipher or None

        super(ZlibArchiveWriter, self).__init__(archive_path, logical_toc)


    def add(self, entry):
        name, path, typ = entry
        if typ == 'PYMODULE':
            typ = PYZ_TYPE_MODULE
            if path in ('-', None):
                # This is a NamespacePackage, modulegraph marks them
                # by using the filename '-'. (But wants to use None,
                # so check for None, too, to be forward-compatible.)
                typ = PYZ_TYPE_NSPKG
            else:
                base, ext = os.path.splitext(os.path.basename(path))
                if base == '__init__':
                    typ = PYZ_TYPE_PKG
            data = marshal.dumps(self.code_dict[name])
        else:
            # Any data files, that might be required by pkg_resources.
            typ = PYZ_TYPE_DATA
            with open(path, 'rb') as fh:
                data = fh.read()
            # No need to use forward slash as path-separator here since
            # pkg_resources on Windows back slash as path-separator.

        obj = zlib.compress(data, self.COMPRESSION_LEVEL)

        # First compress then encrypt.
        if self.cipher:
            obj = self.cipher.encrypt(obj)

        self.toc.append((name, (typ, self.lib.tell(), len(obj))))
        self.lib.write(obj)

    def update_headers(self, tocpos):
        """
        add level
        """
        ArchiveWriter.update_headers(self, tocpos)
        self.lib.write(struct.pack('!B', self.cipher is not None))



class CTOC(object):
    """
    A class encapsulating the table of contents of a CArchive.

    When written to disk, it is easily read from C.
    """
    # (structlen, dpos, dlen, ulen, flag, typcd) followed by name
    ENTRYSTRUCT = '!iIIIBB'
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
        if is_win and os.path.sep == '/':
            # When building under MSYS, the above path normalization
            # uses Unix-style separators, so replace them manually.
            nm = nm.replace(os.path.sep, '\\')
        self.data.append((dpos, dlen, ulen, flag, typcd, nm))


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
    LEVEL = 9

    # Cookie - holds some information for the bootloader. C struct format
    # definition. '!' at the beginning means network byte order.
    # C struct looks like:
    #
    #   typedef struct _cookie {
    #       char magic[8]; /* 'MEI\014\013\012\013\016' */
    #       uint32_t len;  /* len of entire package */
    #       uint32_t TOC;  /* pos (rel to start) of TableOfContents */
    #       int  TOClen;   /* length of TableOfContents */
    #       int  pyvers;   /* new in v4 */
    #       char pylibname[64];    /* Filename of Python dynamic library. */
    #   } COOKIE;
    #
    _cookie_format = '!8sIIii64s'
    _cookie_size = struct.calcsize(_cookie_format)

    def __init__(self, archive_path, logical_toc, pylib_name):
        """
        Constructor.

        archive_path path name of file (create empty CArchive if path is None).
        start        is the seekposition within PATH.
        len          is the length of the CArchive (if 0, then read till EOF).
        pylib_name   name of Python DLL which bootloader will use.
        """
        self._pylib_name = pylib_name

        # A CArchive created from scratch starts at 0, no leading bootloader.
        super(CArchiveWriter, self).__init__(archive_path, logical_toc)

    def _start_add_entries(self, path):
        """
        Open an empty archive for addition of entries.
        """
        super(CArchiveWriter, self)._start_add_entries(path)
        # Override parents' toc {} with a class.
        self.toc = CTOC()

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
                  u  (meaning unbuffered)
                  W arg (warning option arg)
                  s  (meaning do site.py processing.
        """
        (nm, pathnm, flag, typcd) = entry[:4]
        # FIXME Could we make the version 5 the default one?
        # Version 5 - allow type 'o' = runtime option.
        code_data = None
        fh = None
        try:
            if typcd in ('o', 'd'):
                ulen = 0
                flag = 0
            elif typcd == 's':
                # If it's a source code file, compile it to a code object and marshall
                # the object so it can be unmarshalled by the bootloader.

                code = get_code_object(nm, pathnm)
                code = strip_paths_in_code(code)

                code_data = marshal.dumps(code)
                ulen = len(code_data)
            elif typcd == 'm':
                fh = open(pathnm, 'rb')
                ulen = os.fstat(fh.fileno()).st_size
                # Check if it is a PYC file
                header = fh.read(4)
                fh.seek(0)
                if header == BYTECODE_MAGIC:
                    # Read whole header and load code.
                    # According to PEP-552, in python versions prior to
                    # 3.7, the PYC header consists of three 32-bit words
                    # (magic, timestamp, and source file size).
                    # From python 3.7 on, the PYC header was extended to
                    # four 32-bit words (magic, flags, and, depending on
                    # the flags, either timestamp and source file size,
                    # or a 64-bit hash).
                    if is_py37:
                        header = fh.read(16)
                    else:
                        header = fh.read(12)
                    code = marshal.load(fh)
                    # Strip paths from code, marshal back into module form.
                    # The header fields (timestamp, size, hash, etc.) are
                    # all referring to the source file, so our modification
                    # of the code object does not affect them, and we can
                    # re-use the original header.
                    code = strip_paths_in_code(code)
                    data = header + marshal.dumps(code)
                    # Create file-like object for timestamp re-write
                    # in the subsequent steps
                    fh = io.BytesIO(data)
                    ulen = len(data)
            else:
                fh = open(pathnm, 'rb')
                ulen = os.fstat(fh.fileno()).st_size
        except IOError:
            print("Cannot find ('%s', '%s', %s, '%s')" % (nm, pathnm, flag, typcd))
            raise

        where = self.lib.tell()
        assert flag in range(3)
        if not fh and not code_data:
            # no need to write anything
            pass
        elif flag == 1:
            comprobj = zlib.compressobj(self.LEVEL)
            if code_data is not None:
                self.lib.write(comprobj.compress(code_data))
            else:
                assert fh
                # We only want to change it for pyc files
                modify_header = typcd in ('M', 'm', 's')
                while 1:
                    buf = fh.read(16*1024)
                    if not buf:
                        break
                    if modify_header:
                        modify_header = False
                        buf = fake_pyc_timestamp(buf)
                    self.lib.write(comprobj.compress(buf))
            self.lib.write(comprobj.flush())

        else:
            if code_data is not None:
                self.lib.write(code_data)
            else:
                assert fh
                while 1:
                    buf = fh.read(16*1024)
                    if not buf:
                        break
                    self.lib.write(buf)

        dlen = self.lib.tell() - where
        if typcd == 'm':
            if pathnm.find('.__init__.py') > -1:
                typcd = 'M'

        if fh:
            fh.close()

        # Record the entry in the CTOC
        self.toc.add(where, dlen, ulen, flag, typcd, nm)


    def save_trailer(self, tocpos):
        """
        Save the table of contents and the cookie for the bootlader to
        disk.

        CArchives can be opened from the end - the cookie points
        back to the start.
        """
        tocstr = self.toc.tobinary()
        self.lib.write(tocstr)
        toclen = len(tocstr)

        # now save teh cookie
        total_len = tocpos + toclen + self._cookie_size
        pyvers = sys.version_info[0] * 10 + sys.version_info[1]
        # Before saving cookie we need to convert it to corresponding
        # C representation.
        cookie = struct.pack(self._cookie_format, self.MAGIC, total_len,
                             tocpos, toclen, pyvers,
                             self._pylib_name.encode('ascii'))
        self.lib.write(cookie)
