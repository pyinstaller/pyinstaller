#-----------------------------------------------------------------------------
# Copyright (c) 2013-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
This CArchiveReader is used only by the archieve_viewer utility.
"""

# TODO clean up this module

import os
import struct

from PyInstaller.loader.pyimod02_archive import ArchiveReader


class NotAnArchiveError(Exception):
    pass


class CTOCReader:
    """
    A class encapsulating the table of contents of a CArchive.

    When written to disk, it is easily read from C.
    """
    # (structlen, dpos, dlen, ulen, flag, typcd) followed by name
    ENTRYSTRUCT = '!iIIIBB'
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
            slen, dpos, dlen, ulen, flag, typcd = struct.unpack(self.ENTRYSTRUCT, s[p:p + self.ENTRYLEN])
            nmlen = slen - self.ENTRYLEN
            p = p + self.ENTRYLEN
            nm, = struct.unpack('%is' % nmlen, s[p:p + nmlen])
            p = p + nmlen
            # nm may have up to 15 bytes of padding
            nm = nm.rstrip(b'\0')
            nm = nm.decode('utf-8')
            typcd = chr(typcd)
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


class CArchiveReader(ArchiveReader):
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
        super().__init__(archive_path, start)

    def checkmagic(self):
        """
        Verify that self is a valid CArchive.

        Magic signature is at end of the archive.

        This function is used by ArchiveViewer.py utility.
        """
        # Magic is at EOF; if we're embedded, we need to figure where that is.
        if self.length:
            self.lib.seek(self.start + self.length, 0)
        else:
            self.lib.seek(0, os.SEEK_END)
        end_pos = self.lib.tell()

        SEARCH_CHUNK_SIZE = 8192
        magic_offset = -1
        while end_pos >= len(self.MAGIC):
            start_pos = max(end_pos - SEARCH_CHUNK_SIZE, 0)
            chunk_size = end_pos - start_pos
            # Is the remaining chunk large enough to hold the pattern?
            if chunk_size < len(self.MAGIC):
                break
            # Read and scan the chunk
            self.lib.seek(start_pos, os.SEEK_SET)
            buf = self.lib.read(chunk_size)
            pos = buf.rfind(self.MAGIC)
            if pos != -1:
                magic_offset = start_pos + pos
                break
            # Adjust search location for next chunk; ensure proper overlap
            end_pos = start_pos + len(self.MAGIC) - 1
        if magic_offset == -1:
            raise RuntimeError("%s is not a valid %s archive file" % (self.path, self.__class__.__name__))
        filelen = magic_offset + self._cookie_size
        # Read the whole cookie
        self.lib.seek(magic_offset, os.SEEK_SET)
        buf = self.lib.read(self._cookie_size)
        magic, totallen, tocpos, toclen, pyvers, pylib_name = struct.unpack(self._cookie_format, buf)
        if magic != self.MAGIC:
            raise RuntimeError("%s is not a valid %s archive file" % (self.path, self.__class__.__name__))

        self.pkg_start = filelen - totallen
        if self.length:
            if totallen != self.length or self.pkg_start != self.start:
                raise RuntimeError('Problem with embedded archive in %s' % self.path)
        # Verify presence of Python library name.
        if not pylib_name:
            raise RuntimeError('Python library filename not defined in archive.')
        self.tocpos, self.toclen = tocpos, toclen

    def loadtoc(self):
        """
        Load the table of contents into memory.
        """
        self.toc = CTOCReader()
        self.lib.seek(self.pkg_start + self.tocpos)
        tocstr = self.lib.read(self.toclen)
        self.toc.frombinary(tocstr)

    def extract(self, name):
        """
        Get the contents of an entry.

        NAME is an entry name OR the index to the TOC.

        Return the tuple (ispkg, contents).
        For non-Python resources, ispkg is meaningless (and 0).
        Used by the import mechanism.
        """
        if isinstance(name, str):
            ndx = self.toc.find(name)
            if ndx == -1:
                return None
        else:
            ndx = name
        dpos, dlen, ulen, flag, typcd, nm = self.toc.get(ndx)

        with self.lib:
            self.lib.seek(self.pkg_start + dpos)
            rslt = self.lib.read(dlen)

        if flag == 1:
            import zlib
            rslt = zlib.decompress(rslt)
        if typcd == 'M':
            return 1, rslt

        return typcd == 'M', rslt

    def contents(self):
        """
        Return the names of the entries.
        """
        rslt = []
        for dpos, dlen, ulen, flag, typcd, nm in self.toc:
            rslt.append(nm)
        return rslt

    def openEmbedded(self, name):
        """
        Open a CArchive of name NAME embedded within this CArchive.

        This function is used by ArchiveViewer.py utility.
        """
        ndx = self.toc.find(name)

        if ndx == -1:
            raise KeyError("Member '%s' not found in %s" % (name, self.path))
        dpos, dlen, ulen, flag, typcd, nm = self.toc.get(ndx)

        if typcd not in "zZ":
            raise NotAnArchiveError('%s is not an archive' % name)

        if flag:
            raise ValueError('Cannot open compressed archive %s in place' % name)
        return CArchiveReader(self.path, self.pkg_start + dpos, dlen)
