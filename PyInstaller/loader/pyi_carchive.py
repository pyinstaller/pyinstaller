#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Subclass of Archive that can be understood by a C program (see launch.c).
"""


import struct
import sys
import zlib
import os


import pyi_archive

class NotAnArchiveError(Exception): pass

class CTOC(object):
    """
    A class encapsulating the table of contents of a CArchive.

    When written to disk, it is easily read from C.
    """
    ENTRYSTRUCT = '!iiiiBB'  # (structlen, dpos, dlen, ulen, flag, typcd) followed by name
    ENTRYLEN = struct.calcsize(ENTRYSTRUCT)

    def __init__(self):
        self.data = []

    def frombinary(self, s):
        """
        Decode the binary string into an in memory list.

        S is a binary string.
        """
        p = 0

        while p < len(s):
            (slen, dpos, dlen, ulen, flag, typcd) = struct.unpack(self.ENTRYSTRUCT,
                                                        s[p:p + self.ENTRYLEN])
            nmlen = slen - self.ENTRYLEN
            p = p + self.ENTRYLEN
            (nm,) = struct.unpack('%is' % nmlen, s[p:p + nmlen])
            p = p + nmlen
            # nm may have up to 15 bytes of padding
            nm = nm.rstrip(b'\0')
            nm = nm.decode('utf-8')
            typcd = chr(typcd)
            self.data.append((dpos, dlen, ulen, flag, typcd, nm))

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

        return ''.join(rslt)

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
        # Import module here since it might not be available during bootstrap
        # and loading pyi_carchive module could fail.
        import os.path
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


class CArchive(pyi_archive.Archive):
    """
    An Archive subclass that can hold arbitrary data.

    This class encapsulates all files that are bundled within an executable.
    It can contain ZlibArchive (Python .pyc files), dlls, Python C extensions
    and all other data files that are bundled in --onefile mode.

    Easily handled from C or from Python.
    """
    # MAGIC is usefull to verify that conversion of Python data types
    # to C structure and back works properly.
    MAGIC = 'MEI\014\013\012\013\016'
    HDRLEN = 0
    TOCTMPLT = CTOC
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
        super(CArchive, self).__init__(archive_path, start)

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

    # TODO Verify usefulness of this method.
    def copy_from(self, arch):
        """
        Copy an entire archive into the current archive, updating TOC but
        NOT writing it, to allow additions of files to end of archive.
        Must be first action after _start_add_entries() since bootloader is
        first.
        """
        self.pkg_start = arch.pkg_start
        size = arch.pkg_start + arch.TOCPOS
        blksize = 4096
        arch.lib.seek(0)
        # copy the whole file with some blocking for reads
        while (size > 0):
            self.lib.write(arch.lib.read(min(blksize, size)))
            size -= blksize

        for tocentry in arch.toc:
            self.toc.add(*tocentry)

    def checkmagic(self):
        """
        Verify that self is a valid CArchive.

        Magic signature is at end of the archive.

        This fuction is used by ArchiveViewer.py utility.
        """
        # Magic is at EOF; if we're embedded, we need to figure where that is.
        if self.length:
            self.lib.seek(self.start + self.length, 0)
        else:
            self.lib.seek(0, 2)
        filelen = self.lib.tell()
        if self.length:
            self.lib.seek(self.start + self.length - self._cookie_size, 0)
        else:
            self.lib.seek(-self._cookie_size, 2)
        (magic, totallen, tocpos, toclen, pyvers, pylib_name) = struct.unpack(
                self._cookie_format, self.lib.read(self._cookie_size))
        if magic != self.MAGIC:
            raise RuntimeError("%s is not a valid %s archive file" %
                    (self.path, self.__class__.__name__))
        self.pkg_start = filelen - totallen
        if self.length:
            if totallen != self.length or self.pkg_start != self.start:
                raise RuntimeError('Problem with embedded archive in %s' %
                        self.path)
        # Verify presence of Python library name.
        if not pylib_name:
            raise RuntimeError('Python library filename not defined in archive.')
        self.tocpos, self.toclen = tocpos, toclen

    def loadtoc(self):
        """
        Load the table of contents into memory.
        """
        self.toc = self.TOCTMPLT()
        self.lib.seek(self.pkg_start + self.tocpos)
        tocstr = self.lib.read(self.toclen)
        self.toc.frombinary(tocstr)

    def extract(self, name):
        """
        Get the contents of an entry.

        NAME is an entry name OR the index to the TOC.

        Return the tuple (ispkg, contents).
        For non-Python resoures, ispkg is meaningless (and 0).
        Used by the import mechanism.
        """
        if type(name) == type(''):
            ndx = self.toc.find(name)
            if ndx == -1:
                return None
        else:
            ndx = name
        (dpos, dlen, ulen, flag, typcd, nm) = self.toc.get(ndx)

        self.lib.seek(self.pkg_start + dpos)
        rslt = self.lib.read(dlen)

        if flag == 1:
            rslt = zlib.decompress(rslt)
        if typcd == 'M':
            return (1, rslt)

        return (typcd == 'M', rslt)

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
                postfix = ''
                flag = 0
            elif typcd == 's':
                # If it's a source code file, add \0 terminator as it will be
                # executed as-is by the bootloader.
                fh = open(pathnm, 'rU')
                postfix = '\n\0'
                ulen = os.fstat(fh.fileno()).st_size + len(postfix)
            else:
                fh = open(pathnm, 'rb')
                postfix = ''
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
                tocpos, self.toclen, pyvers, self._pylib_name)
        self.lib.write(cookie)

    def openEmbedded(self, name):
        """
        Open a CArchive of name NAME embedded within this CArchive.

        This fuction is used by ArchiveViewer.py utility.
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
        return CArchive(self.path, self.pkg_start + dpos, dlen)
