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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os, sys, iu, imp
class Win32ImportDirector(iu.ImportDirector):
    def __init__(self):
        self.path = sys.path[0] # since I run as a hook, sys.path probably hasn't been mucked with
        if hasattr(sys, 'version_info'):
            self.suffix = '%d%d'%(sys.version_info[0],sys.version_info[1])
        else:
            self.suffix = '%s%s' % (sys.version[0], sys.version[2])
    def getmod(self, nm):
        fnm = os.path.join(self.path, nm+self.suffix+'.dll')
        try:
            fp = open(fnm, 'rb')
        except:
            return None
        else:
            mod = imp.load_module(nm, fp, fnm, ('.dll', 'rb', imp.C_EXTENSION))
            mod.__file__ = fnm
            return mod
sys.importManager.metapath.insert(1, Win32ImportDirector())
