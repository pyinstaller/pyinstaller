#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Utilities to create data structures for embedding Python modules and additional files into the executable.
"""

# While an Archive is really an abstraction for any "filesystem within a file", it is tuned for use with
# imputil.FuncImporter. This assumes it contains python code objects, indexed by the the internal name (ie, no '.py').
#
# See pyi_carchive.py for a more general archive (contains anything) that can be understood by a C program.

import marshal
import os
import shutil
import struct
import sys
import zlib
from types import CodeType

from PyInstaller.building.utils import get_code_object, strip_paths_in_code
from PyInstaller.compat import BYTECODE_MAGIC, is_win, strict_collect_mode
from PyInstaller.loader.pyimod01_archive import PYZ_TYPE_DATA, PYZ_TYPE_MODULE, PYZ_TYPE_NSPKG, PYZ_TYPE_PKG


class ArchiveWriter:
    """
    A base class for a repository of python code objects. The extract method is used by imputil.ArchiveImporter to
    get code objects by name (fully qualified name), so an end-user "import a.b" becomes extract('a.__init__') and
    extract('a.b').
    """
    MAGIC = b'PYL\0'
    HDRLEN = 12  # default is MAGIC followed by python's magic, int pos of toc
    TOCPOS = 8

    def __init__(self, archive_path, logical_toc):
        """
        Create an archive file of name 'archive_path'. logical_toc is a 'logical TOC', a list of (name, path, ...),
        where name is the internal name (e.g., 'a') and path is a file to get the object from (e.g., './a.pyc').
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
        # Create an empty table of contents. Use a list to support reproducible builds.
        self.toc = []

    def _add_from_table_of_contents(self, toc):
        """
        Add entries from a logical TOC (without absolute positioning info).
        An entry in a logical TOC is a tuple:
          entry[0] is name (under which it will be saved).
          entry[1] is fullpathname of the file.
          entry[2] is a flag for its storage format (True or 1 if compressed).
          entry[3] is the entry's type code.
        """
        for toc_entry in toc:
            self.add(toc_entry)  # The guts of the archive.

    def _finalize(self):
        """
        Finalize an archive which has been opened using _start_add_entries(), writing any needed padding and the
        table of contents.
        """
        toc_pos = self.lib.tell()
        self.save_trailer(toc_pos)
        if self.HDRLEN:
            self.update_headers(toc_pos)
        self.lib.close()

    # manages keeping the internal TOC and the guts in sync #
    def add(self, entry):
        """
        Override this to influence the mechanics of the Archive. Assumes entry is a seq beginning with (nm, pth, ...),
        where nm is the key by which we will be asked for the object. pth is the name of where we find the object.
        Overrides of get_obj_from can make use of further elements in entry.
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
        Default - toc is a dict Gets marshaled to self.lib
        """
        try:
            self.lib.write(marshal.dumps(self.toc))
        # If the TOC to be marshalled contains an unmarshallable object, Python raises a cryptic exception providing no
        # details on why such object is unmarshallable. Correct this by iteratively inspecting the TOC for
        # unmarshallable objects.
        except ValueError as exception:
            if str(exception) == 'unmarshallable object':
                # List of all marshallable types.
                MARSHALLABLE_TYPES = {
                    bool, int, float, complex, str, bytes, bytearray, tuple, list, set, frozenset, dict, CodeType
                }
                for module_name, module_tuple in self.toc.items():
                    if type(module_name) not in MARSHALLABLE_TYPES:
                        print('Module name "%s" (%s) unmarshallable.' % (module_name, type(module_name)))
                    if type(module_tuple) not in MARSHALLABLE_TYPES:
                        print(
                            'Module "%s" tuple "%s" (%s) unmarshallable.' %
                            (module_name, module_tuple, type(module_tuple))
                        )
                    elif type(module_tuple) == tuple:
                        for i in range(len(module_tuple)):
                            if type(module_tuple[i]) not in MARSHALLABLE_TYPES:
                                print(
                                    'Module "%s" tuple index %s item "%s" (%s) unmarshallable.' %
                                    (module_name, i, module_tuple[i], type(module_tuple[i]))
                                )

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
    ZlibArchive - an archive with compressed entries. Archive is read from the executable created by PyInstaller.

    This archive is used for bundling python modules inside the executable.

    NOTE: The whole ZlibArchive (PYZ) is compressed, so it is not necessary to compress individual modules.
    """
    MAGIC = b'PYZ\0'
    TOCPOS = 8
    HDRLEN = ArchiveWriter.HDRLEN + 5
    COMPRESSION_LEVEL = 6  # Default level of the 'zlib' module from Python.

    def __init__(self, archive_path, logical_toc, code_dict=None, cipher=None):
        """
        code_dict      dict containing module code objects from ModuleGraph.
        """
        # Keep references to module code objects constructed by ModuleGraph to avoid writing .pyc/pyo files to hdd.
        self.code_dict = code_dict or {}
        self.cipher = cipher or None

        super().__init__(archive_path, logical_toc)

    def add(self, entry):
        name, src_path, typecode = entry
        if typecode == 'PYMODULE':
            typecode = PYZ_TYPE_MODULE
            if src_path in ('-', None):
                # This is a NamespacePackage, modulegraph marks them by using the filename '-'. (But wants to use None,
                # so check for None, too, to be forward-compatible.)
                typecode = PYZ_TYPE_NSPKG
            else:
                src_basename, _ = os.path.splitext(os.path.basename(src_path))
                if src_basename == '__init__':
                    typecode = PYZ_TYPE_PKG
            data = marshal.dumps(self.code_dict[name])
        else:
            # Any data files, that might be required by pkg_resources.
            typecode = PYZ_TYPE_DATA
            with open(src_path, 'rb') as fh:
                data = fh.read()
            # No need to use forward slash as path-separator here since pkg_resources on Windows back slash as
            # path-separator.

        obj = zlib.compress(data, self.COMPRESSION_LEVEL)

        # First compress then encrypt.
        if self.cipher:
            obj = self.cipher.encrypt(obj)

        self.toc.append((name, (typecode, self.lib.tell(), len(obj))))
        self.lib.write(obj)

    def update_headers(self, tocpos):
        """
        Add level.
        """
        ArchiveWriter.update_headers(self, tocpos)
        self.lib.write(struct.pack('!B', self.cipher is not None))


class CTOC:
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
            # Encode all names using UTF-8. This should be safe as standard python modules only contain ascii-characters
            # (and standard shared libraries should have the same), and thus the C-code still can handle this correctly.
            nm = nm.encode('utf-8')
            nmlen = len(nm) + 1  # add 1 for a '\0'
            # align to 16 byte boundary so xplatform C can read
            toclen = nmlen + self.ENTRYLEN
            if toclen % 16 == 0:
                pad = b'\0'
            else:
                padlen = 16 - (toclen % 16)
                pad = b'\0' * padlen
                nmlen = nmlen + padlen
            rslt.append(
                struct.pack(
                    self.ENTRYSTRUCT + '%is' % nmlen, nmlen + self.ENTRYLEN, dpos, dlen, ulen, flag, ord(typcd),
                    nm + pad
                )
            )

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
        # Ensure forward slashes in paths are on Windows converted to back slashes '\\' since on Windows the bootloader
        # works only with back slashes.
        nm = os.path.normpath(nm)
        if is_win and os.path.sep == '/':
            # When building under MSYS, the above path normalization uses Unix-style separators, so replace them
            # manually.
            nm = nm.replace(os.path.sep, '\\')
        self.data.append((dpos, dlen, ulen, flag, typcd, nm))


class CArchiveWriter(ArchiveWriter):
    """
    An Archive subclass that can hold arbitrary data.

    This class encapsulates all files that are bundled within an executable. It can contain ZlibArchive (Python .pyc
    files), dlls, Python C extensions and all other data files that are bundled in --onefile mode.

    Easily handled from C or from Python.
    """
    # MAGIC is useful to verify that conversion of Python data types to C structure and back works properly.
    MAGIC = b'MEI\014\013\012\013\016'
    HDRLEN = 0
    LEVEL = 9

    # Cookie - holds some information for the bootloader. C struct format definition. '!' at the beginning means network
    # byte order. C struct looks like:
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

        self._collected_names = set()  # Track collected names for strict package mode.

        # A CArchive created from scratch starts at 0, no leading bootloader.
        super().__init__(archive_path, logical_toc)

    def _start_add_entries(self, path):
        """
        Open an empty archive for addition of entries.
        """
        super()._start_add_entries(path)
        # Override parents' toc {} with a class.
        self.toc = CTOC()

    def add(self, entry):
        """
        Add an ENTRY to the CArchive.

        ENTRY must have:
          entry[0] is name (under which it will be saved).
          entry[1] is fullpathname of the file.
          entry[2] is a flag for it's storage format (0==uncompressed, 1==compressed)
          entry[3] is the entry's type code.
            If the type code is 'o':
              entry[0] is the runtime option
              eg: v  (meaning verbose imports)
                  u  (meaning unbuffered)
                  W arg (warning option arg)
                  s  (meaning do site.py processing.
        """
        dest, source, compress, type = entry[:4]

        # Strict pack/collect mode: keep track of the destination names, and raise an error if we try to add a duplicate
        # (a file with same destination name, subject to OS case normalization rules).
        if strict_collect_mode:
            normalized_dest = None
            if type in ('o', 's', 'm', 'M'):
                # Exempt options, python source script, and modules from the check
                pass
            else:
                # Everything else; normalize the case
                normalized_dest = os.path.normcase(dest)
            # Check for existing entry, if applicable
            if normalized_dest:
                if normalized_dest in self._collected_names:
                    raise ValueError(
                        f"Attempting to collect a duplicated file into CArchive: {normalized_dest} (type: {type})"
                    )
                self._collected_names.add(normalized_dest)

        try:
            if type == 'o':
                return self._write_blob(b"", dest, type)

            elif type == 'd':
                # Dependency; merge source (= reference path prefix) and dest (= name) into single-string format that is
                # parsed by bootloader.
                return self._write_blob(b"", f"{source}:{dest}", type)

            if type == 's':
                # If it is a source code file, compile it to a code object and marshal the object, so it can be
                # unmarshalled by the bootloader.
                code = get_code_object(dest, source)
                code = strip_paths_in_code(code)
                return self._write_blob(marshal.dumps(code), dest, type, compress=compress)

            elif type in ('m', 'M'):
                # Read the PYC file
                with open(source, "rb") as f:
                    data = f.read()
                assert data[:4] == BYTECODE_MAGIC
                # Skip the PYC header, load the code object.
                code = marshal.loads(data[16:])
                code = strip_paths_in_code(code)
                # These module entries are loaded and executed within the bootloader, which requires only the code
                # object, without the PYC header.
                return self._write_blob(marshal.dumps(code), dest, type, compress=compress)

            else:
                self._write_file(source, dest, type, compress=compress)

        except IOError:
            print("Cannot find ('%s', '%s', %s, '%s')" % (dest, source, compress, type))
            raise

    def _write_blob(self, blob: bytes, dest, type, compress=False):
        """
        Write the binary contents (**blob**) of a small file to both the archive and its table of contents.
        """
        start = self.lib.tell()
        length = len(blob)
        if compress:
            blob = zlib.compress(blob, level=self.LEVEL)
        self.lib.write(blob)
        self.toc.add(start, len(blob), length, int(compress), type, dest)

    def _write_file(self, source, dest, type, compress=False):
        """
        Stream copy a large file into the archive and update the table of contents.
        """
        start = self.lib.tell()
        length = os.stat(source).st_size
        with open(source, 'rb') as f:
            if compress:
                buffer = bytearray(16 * 1024)
                compressor = zlib.compressobj(self.LEVEL)
                while 1:
                    read = f.readinto(buffer)
                    if not read:
                        break
                    self.lib.write(compressor.compress(buffer[:read]))
                self.lib.write(compressor.flush())

            else:
                shutil.copyfileobj(f, self.lib)
        self.toc.add(start, self.lib.tell() - start, length, int(compress), type, dest)

    def save_trailer(self, tocpos):
        """
        Save the table of contents and the cookie for the bootlader to disk.

        CArchives can be opened from the end - the cookie points back to the start.
        """
        tocstr = self.toc.tobinary()
        self.lib.write(tocstr)
        toclen = len(tocstr)

        # now save the cookie
        total_len = tocpos + toclen + self._cookie_size
        pyvers = sys.version_info[0] * 100 + sys.version_info[1]
        # Before saving cookie we need to convert it to corresponding C representation.
        cookie = struct.pack(
            self._cookie_format, self.MAGIC, total_len, tocpos, toclen, pyvers, self._pylib_name.encode('ascii')
        )
        self.lib.write(cookie)


class SplashWriter(ArchiveWriter):
    """
    This ArchiveWriter bundles the data for the splash screen resources.

    Splash screen resources will be added as an entry into the CArchive with the typecode ARCHIVE_ITEM_SPLASH.
    This writer creates the bundled information in the archive.
    """
    # This struct describes the splash resources as it will be in an buffer inside the bootloader. All necessary parts
    # are bundled, the *_len and *_offset fields describe the data beyond this header definition.
    # Whereas script and image fields are binary data, the requirements fields describe an array of strings. Each string
    # is null-terminated in order to easily iterate over this list from within C.
    #
    #   typedef struct _splash_data_header {
    #       char tcl_libname[16];  /* Name of tcl library, e.g. tcl86t.dll */
    #       char tk_libname[16];   /* Name of tk library, e.g. tk86t.dll */
    #       char tk_lib[16];       /* Tk Library generic, e.g. "tk/" */
    #       char rundir[16];       /* temp folder inside extraction path in
    #                               * which the dependencies are extracted */
    #
    #       int script_len;        /* Length of the script */
    #       int script_offset;     /* Offset (rel to start) of the script */
    #
    #       int image_len;         /* Length of the image data */
    #       int image_offset;      /* Offset (rel to start) of the image */
    #
    #       int requirements_len;
    #       int requirements_offset;
    #
    #   } SPLASH_DATA_HEADER;
    #
    _header_format = '!16s 16s 16s 16s ii ii ii'
    HDRLEN = struct.calcsize(_header_format)

    # The created resource will be compressed by the CArchive, so no need to compress the data here.

    def __init__(self, archive_path, name_list, tcl_libname, tk_libname, tklib, rundir, image, script):
        """
        Custom writer for splash screen resources which will be bundled into the CArchive as an entry.

        :param archive_path: The filename of the archive to create
        :param name_list: List of filenames for the requirements array
        :param str tcl_libname: Name of the tcl shared library file
        :param str tk_libname: Name of the tk shared library file
        :param str tklib: Root of tk library (e.g. tk/)
        :param str rundir: Unique path to extract requirements to
        :param Union[str, bytes] image: Image like object
        :param str script: The tcl/tk script to execute to create the screen.
        """
        self._tcl_libname = tcl_libname
        self._tk_libname = tk_libname
        self._tklib = tklib
        self._rundir = rundir

        self._image = image
        self._image_len = 0
        self._image_offset = 0

        self._script = script
        self._script_len = 0
        self._script_offset = 0

        self._requirements_len = 0
        self._requirements_offset = 0

        super().__init__(archive_path, name_list)

    def add(self, name):
        """
        This methods adds a name to the requirement list in the splash data. This list (more an array) contains the
        names of all files the bootloader needs to extract before the splash screen can be started. The
        implementation terminates every name with a null-byte, that keeps the list short memory wise and makes it
        iterable from C.
        """
        name = name.encode('utf-8')
        self.lib.write(name + b'\0')
        self._requirements_len += len(name) + 1  # zero byte at the end

    def update_headers(self, tocpos):
        """
        Updates the offsets of the fields.

        This function is called after self.save_trailer().
        :param tocpos:
        :return:
        """
        self.lib.seek(self.start)
        self.lib.write(
            struct.pack(
                self._header_format,
                self._tcl_libname.encode("utf-8"),
                self._tk_libname.encode("utf-8"),
                self._tklib.encode("utf-8"),
                self._rundir.encode("utf-8"),
                self._script_len,
                self._script_offset,
                self._image_len,
                self._image_offset,
                self._requirements_len,
                self._requirements_offset,
            )
        )

    def save_trailer(self, script_pos):
        """
        Adds the image and script.
        """
        self._requirements_offset = script_pos - self._requirements_len

        self._script_offset = script_pos
        self.save_script()
        self._image_offset = self.lib.tell()
        self.save_image()

    def save_script(self):
        """
        Add the tcl/tk script into the archive. This strips out every comment in the source to save some space.
        """
        self._script_len = len(self._script)
        self.lib.write(self._script.encode("utf-8"))

    def save_image(self):
        """
        Copy the image into the archive. If self._image are bytes the buffer will be written directly into the archive,
        otherwise it is assumed to be a path and the file will be written into it.
        """
        if isinstance(self._image, bytes):
            # image was converted by PIL/Pillow
            buf = self._image
            self.lib.write(self._image)
        else:
            # Copy image to lib
            with open(self._image, 'rb') as image_file:
                buf = image_file.read()

        self._image_len = len(buf)
        self.lib.write(buf)
