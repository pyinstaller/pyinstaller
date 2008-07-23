# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

_orig_open = open

class _BkFile:
    def __init__(self, file, mode, bufsize):
        import os
        self.__filename = file
        self.__backup = file + '~'
        try:
            os.unlink(self.__backup)
        except os.error:
            pass
        try:
            os.rename(file, self.__backup)
        except os.error:
            self.__backup = None
        self.__file = _orig_open(file, mode, bufsize)
        self.closed = self.__file.closed
        self.fileno = self.__file.fileno
        self.flush = self.__file.flush
        self.isatty = self.__file.isatty
        self.mode = self.__file.mode
        self.name = self.__file.name
        self.read = self.__file.read
        self.readinto = self.__file.readinto
        self.readline = self.__file.readline
        self.readlines = self.__file.readlines
        self.seek = self.__file.seek
        self.softspace = self.__file.softspace
        self.tell = self.__file.tell
        self.truncate = self.__file.truncate
        self.write = self.__file.write
        self.writelines = self.__file.writelines

    def close(self):
        self.__file.close()
        if self.__backup is None:
            return
        try:
            from cmp import do_cmp
        except:
            from filecmp import cmp
            do_cmp = cmp
        # don't use cmp.cmp because of NFS bugs :-( and
        # anyway, the stat mtime values differ so do_cmp will
        # most likely be called anyway
        if do_cmp(self.__backup, self.__filename):
            import os
            os.unlink(self.__filename)
            os.rename(self.__backup, self.__filename)

def open(file, mode = 'r', bufsize = -1):
    if 'w' not in mode:
        return _orig_open(file, mode, bufsize)
    return _BkFile(file, mode, bufsize)
