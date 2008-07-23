#!/usr/bin/env python
#
# Make .eggs and zipfiles available at runtime
#
# Copyright (C) 2008 Hartmut Goebel <h.goebel@goebel-consult.de>
# Licence: GNU General Public License version 3 (GPL v3)
#
# This file is part of PyInstaller <http://www.pyinstaller.org>
#
# pyinstaller is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyinstaller is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
from tempfile import mkstemp

import carchive

MEIDIR = os.environ['_MEIPASS2']

def extract_resource(zip_path):
    if zip_path in index:
        # 'directory' entry: recursivly extract all member
        for name in index[zip_path]:
            last = extract_resource(os.path.join(zip_path, name))
        # return the real extracted directory name
        return os.path.dirname(last)

    # 'file' entry: extract it
    try:
        real_path = os.path.join(MEIDIR, *zip_path.split(os.sep))

        if os.path.isfile(real_path):
            stat = os.stat(real_path)
            size = content[zip_path][1]
            if stat.st_size==size: # and stat.st_mtime==timestamp:
                # size and stamp match, don't bother extracting
                return real_path

        outf, tmpnam = mkstemp(".$extract", dir=os.path.dirname(real_path))
        os.write(outf, archive.extract(zip_path)[1])
        os.close(outf)
        try:
            os.rename(tmpnam, real_path)
        except os.error:
            if os.path.isfile(real_path):
                stat = os.stat(real_path)
                # todo: check timestamp (compare with sys.executable)
                if stat.st_size == size:
                    # size and stamp match, somebody did it just ahead of
                    # us, so we're done
                    return real_path
                elif os.name=='nt':     # Windows, del old file and retry
                    unlink(real_path)
                    os.rename(tmpnam, real_path)
                    return real_path
            raise

    except os.error:
        # todo: report a user-friendly error
        raise
    return real_path

#---

archive = carchive.CArchive(sys.executable)
archive.loadtoc()

# get contents of archive in a format more suitable for us
# list only zipfiles (typcd 'Z') and eggs (typcd 'E')
contents = dict([(path, (typcd, ulen))
                 for (dpos, dlen, ulen, flag, typcd, path) in archive.toc
                 if typcd in 'EZ'])

# build index for recursivly extracting directories
index = {}
for path in contents:
    parts = path.split(os.sep)
    while parts:
        parent = os.sep.join(parts[:-1])
        if parent in index:
            index[parent].append(parts[-1])
            break
        else:
            index[parent] = [parts.pop()]

# Add the zipfiles to sys.path
for zip_path, (typcd, ulen) in contents.items():
    sys.path.append(extract_resource(zip_path))
