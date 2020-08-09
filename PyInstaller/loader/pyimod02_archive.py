#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# TODO clean up this module

# Subclasses may not need marshal or struct, but since they're
# builtin, importing is safe.
#
# While an Archive is really an abstraction for any "filesystem
# within a file", it is tuned for use with imputil.FuncImporter.
# This assumes it contains python code objects, indexed by the
# the internal name (ie, no '.py').

# See pyi_carchive.py for a more general archive (contains anything)
# that can be understood by a C program.


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.

import marshal
import struct
import sys
import zlib
import _thread as thread


# For decrypting Python modules.
CRYPT_BLOCK_SIZE = 16


# content types for PYZ
PYZ_TYPE_MODULE = 0
PYZ_TYPE_PKG = 1
PYZ_TYPE_DATA = 2

class FilePos(object):
    """
    This class keeps track of the file object representing and current position
    in a file.
    """
    def __init__(self):
        # The file object representing this file.
        self.file = None
        # The position in the file when it was last closed.
        self.pos = 0


class ArchiveFile(object):
    """
    File class support auto open when access member from file object
    This class is use to avoid file locking on windows
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._filePos = {}

    def local(self):
        """
        Return an instance of FilePos for the current thread. This is a crude
        # re-implementation of threading.local, which isn't a built-in module
        # and therefore isn't available.
        """
        ti = thread.get_ident()
        if ti not in self._filePos:
            self._filePos[ti] = FilePos()
        return self._filePos[ti]

    def __getattr__(self, name):
        """
        Make this class act like a file, by invoking most methods on its
        underlying file object.
        """
        file = self.local().file
        assert file
        return getattr(file, name)

    def __enter__(self):
        """
        Open file and seek to pos record from last close.
        """
        # The file shouldn't be open yet.
        fp = self.local()
        assert not fp.file
        # Open the file and seek to the last position.
        fp.file = open(*self.args, **self.kwargs)
        fp.file.seek(fp.pos)

    def __exit__(self, type, value, traceback):
        """
        Close file and record pos.
        """
        # The file should still be open.
        fp = self.local()
        assert fp.file

        # Close the file and record its position.
        fp.pos = fp.file.tell()
        fp.file.close()
        fp.file = None


class ArchiveReadError(RuntimeError):
    pass


class ArchiveReader(object):
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
    os = None
    _bincache = None

    def __init__(self, path=None, start=0):
        """
        Initialize an Archive. If path is omitted, it will be an empty Archive.
        """
        self.toc = None
        self.path = path
        self.start = start

        # In Python 3 module 'imp' is no longer built-in and we cannot use it.
        # There is for Python 3 another way how to obtain magic value.
        # We cannot use at this bootstrap stage importlib directly
        # but its frozen variant.
        import _frozen_importlib
        self.pymagic = _frozen_importlib._bootstrap_external.MAGIC_NUMBER

        if path is not None:
            self.lib = ArchiveFile(self.path, 'rb')
            with self.lib:
                self.checkmagic()
                self.loadtoc()


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
        # Use marshal.loads() since load() arg must be a file object
        # Convert the read list into a dict for faster access
        self.toc = dict(marshal.loads(self.lib.read()))

    ######## This is what is called by FuncImporter #######
    ## Since an Archive is flat, we ignore parent and modname.
    #XXX obsolete - imputil only code
    ##  def get_code(self, parent, modname, fqname):
    ##      pass

    def is_package(self, name):
        ispkg, pos = self.toc.get(name, (0, None))
        if pos is None:
            return None
        return bool(ispkg)

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


class Cipher(object):
    """
    This class is used only to decrypt Python modules.
    """
    def __init__(self):
        # At build-type the key is given to us from inside the spec file, at
        # bootstrap-time, we must look for it ourselves by trying to import
        # the generated 'pyi_crypto_key' module.
        import pyimod00_crypto_key
        key = pyimod00_crypto_key.key

        assert type(key) is str
        if len(key) > CRYPT_BLOCK_SIZE:
            self.key = key[0:CRYPT_BLOCK_SIZE]
        else:
            self.key = key.zfill(CRYPT_BLOCK_SIZE)
        assert len(self.key) == CRYPT_BLOCK_SIZE

        import tinyaes
        self._aesmod = tinyaes
        # Issue #1663: Remove the AES module from sys.modules list. Otherwise
        # it interferes with using 'tinyaes' module in users' code.
        del sys.modules['tinyaes']

    def __create_cipher(self, iv):
        # The 'AES' class is stateful, this factory method is used to
        # re-initialize the block cipher class with each call to xcrypt().
        return self._aesmod.AES(self.key.encode(), iv)

    def decrypt(self, data):
        cipher = self.__create_cipher(data[:CRYPT_BLOCK_SIZE])
        return cipher.CTR_xcrypt_buffer(data[CRYPT_BLOCK_SIZE:])


class ZlibArchiveReader(ArchiveReader):
    """
    ZlibArchive - an archive with compressed entries. Archive is read
    from the executable created by PyInstaller.

    This archive is used for bundling python modules inside the executable.

    NOTE: The whole ZlibArchive (PYZ) is compressed so it is not necessary
          to compress single modules with zlib.
    """
    MAGIC = b'PYZ\0'
    TOCPOS = 8
    HDRLEN = ArchiveReader.HDRLEN + 5

    def __init__(self, path=None, offset=None):
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

        super(ZlibArchiveReader, self).__init__(path, offset)

        # Try to import the key module. If the key module is not available
        # then it means that encryption is disabled.
        try:
            import pyimod00_crypto_key
            self.cipher = Cipher()
        except ImportError:
            self.cipher = None

    def is_package(self, name):
        (typ, pos, length) = self.toc.get(name, (0, None, 0))
        if pos is None:
            return None
        return typ == PYZ_TYPE_PKG

    def extract(self, name):
        (typ, pos, length) = self.toc.get(name, (0, None, 0))
        if pos is None:
            return None
        with self.lib:
            self.lib.seek(self.start + pos)
            obj = self.lib.read(length)
        try:
            if self.cipher:
                obj = self.cipher.decrypt(obj)
            obj = zlib.decompress(obj)
            if typ in (PYZ_TYPE_MODULE, PYZ_TYPE_PKG):
                obj = marshal.loads(obj)
        except EOFError as e:
            raise ImportError("PYZ entry '%s' failed to unmarshal" %
                              name) from e
        return typ, obj
