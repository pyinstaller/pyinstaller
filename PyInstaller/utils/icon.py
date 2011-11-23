#! /usr/bin/env python
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

# This code is courtesy of Thomas Heller, who
# has kindly donated it to this project.

RT_ICON = 3
RT_GROUP_ICON = 14
LOAD_LIBRARY_AS_DATAFILE = 2

import struct
import types
try:
    StringTypes = types.StringTypes
except AttributeError:
    StringTypes = [ type("") ]

import PyInstaller.log as logging
logger = logging.getLogger('PyInstaller.icon')

class Structure:
    def __init__(self):
        size = self._sizeInBytes = struct.calcsize(self._format_)
        self._fields_ = list(struct.unpack(self._format_, '\000' * size))
        indexes = self._indexes_ = {}
        for i, nm in enumerate(self._names_):
            indexes[nm] = i

    def dump(self):
        logger.info("DUMP of %s", self)
        for name in self._names_:
            if not name.startswith('_'):
                logger.info("%20s = %s", name, getattr(self, name))
        logger.info("")

    def __getattr__(self, name):
        if name in self._names_:
            index = self._indexes_[name]
            return self._fields_[index]
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError, name

    def __setattr__(self, name, value):
        if name in self._names_:
            index = self._indexes_[name]
            self._fields_[index] = value
        else:
            self.__dict__[name] = value

    def tostring(self):
        return apply(struct.pack, [self._format_,] + self._fields_)

    def fromfile(self, file):
        data = file.read(self._sizeInBytes)
        self._fields_ = list(struct.unpack(self._format_, data))

class ICONDIRHEADER(Structure):
    _names_ = "idReserved", "idType", "idCount"
    _format_ = "hhh"

class ICONDIRENTRY(Structure):
    _names_ = ("bWidth", "bHeight", "bColorCount", "bReserved", "wPlanes",
               "wBitCount", "dwBytesInRes", "dwImageOffset")
    _format_ = "bbbbhhii"

class GRPICONDIR(Structure):
    _names_ = "idReserved", "idType", "idCount"
    _format_ = "hhh"

class GRPICONDIRENTRY(Structure):
    _names_ = ("bWidth", "bHeight", "bColorCount", "bReserved", "wPlanes",
               "wBitCount", "dwBytesInRes", "nID")
    _format_ = "bbbbhhih"

class IconFile:
    def __init__(self, path):
        self.path = path
        file = open(path, "rb")
        self.entries = []
        self.images = []
        header = self.header = ICONDIRHEADER()
        header.fromfile(file)
        for i in range(header.idCount):
            entry = ICONDIRENTRY()
            entry.fromfile(file)
            self.entries.append(entry)
        for e in self.entries:
            file.seek(e.dwImageOffset, 0)
            self.images.append(file.read(e.dwBytesInRes))

    def grp_icon_dir(self):
        return self.header.tostring()

    def grp_icondir_entries(self, id=1):
        data = ""
        for entry in self.entries:
            e = GRPICONDIRENTRY()
            for n in e._names_[:-1]:
                setattr(e, n, getattr(entry, n))
            e.nID = id
            id = id + 1
            data = data + e.tostring()
        return data


def CopyIcons_FromIco(dstpath, srcpath, id=1):
    import win32api #, win32con
    icons = map(IconFile, srcpath)
    logger.info("Updating icons from %s to %s", srcpath, dstpath)

    hdst = win32api.BeginUpdateResource(dstpath, 0)

    iconid = 1
    for i, f in enumerate(icons):
        data = f.grp_icon_dir()
        data = data + f.grp_icondir_entries(iconid)
        win32api.UpdateResource(hdst, RT_GROUP_ICON, i, data)
        logger.info("Writing RT_GROUP_ICON %d resource with %d bytes", i, len(data))
        for data in f.images:
            win32api.UpdateResource(hdst, RT_ICON, iconid, data)
            logger.info("Writing RT_ICON %d resource with %d bytes", iconid, len(data))
            iconid = iconid + 1

    win32api.EndUpdateResource(hdst, 0)

def CopyIcons(dstpath, srcpath):
    import os.path

    if type(srcpath) in StringTypes:
        srcpath = [ srcpath ]

    def splitter(s):
        try:
            srcpath, index = s.split(',')
            return srcpath.strip(), int(index)
        except ValueError:
            return s, None

    srcpath = map(splitter, srcpath)
    logger.info("SRCPATH %s", srcpath)

    if len(srcpath) > 1:
        # At the moment, we support multiple icons only from .ico files
        srcs = []
        for s in srcpath:
            e = os.path.splitext(s[0])[1]
            if e.lower() != '.ico':
                raise ValueError, "multiple icons supported only from .ico files"
            if s[1] is not None:
                raise ValueError, "index not allowed for .ico files"
            srcs.append(s[0])
        return CopyIcons_FromIco(dstpath, srcs)

    srcpath,index = srcpath[0]
    srcext = os.path.splitext(srcpath)[1]
    if srcext.lower() == '.ico':
        return CopyIcons_FromIco(dstpath, [srcpath])
    if index is not None:
        logger.info("Updating icons from %s, %d to %s", srcpath, index, dstpath)
    else:
        logger.info("Updating icons from %s to %s", srcpath, dstpath)
    import win32api #, win32con
    hdst = win32api.BeginUpdateResource(dstpath, 0)
    hsrc = win32api.LoadLibraryEx(srcpath, 0, LOAD_LIBRARY_AS_DATAFILE)
    if index is None:
        grpname = win32api.EnumResourceNames(hsrc, RT_GROUP_ICON)[0]
    elif index >= 0:
        grpname = win32api.EnumResourceNames(hsrc, RT_GROUP_ICON)[index]
    else:
        grpname = -index
    data = win32api.LoadResource(hsrc, RT_GROUP_ICON, grpname)
    win32api.UpdateResource(hdst, RT_GROUP_ICON, grpname, data)
    for iconname in win32api.EnumResourceNames(hsrc, RT_ICON):
        data = win32api.LoadResource(hsrc, RT_ICON, iconname)
        win32api.UpdateResource(hdst, RT_ICON, iconname, data)
    win32api.FreeLibrary(hsrc)
    win32api.EndUpdateResource(hdst, 0)

if __name__ == "__main__":
    import sys

    dstpath = sys.argv[1]
    srcpath = sys.argv[2:]
    CopyIcons(dstpath, srcpath)
