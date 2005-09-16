# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
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

hiddenimports = ['xml.sax.xmlreader','xml.sax.expatreader']

def hook(mod):
    import os, tempfile, sys, string, marshal
    fnm = tempfile.mktemp()
    if string.find(sys.executable, ' ') > -1:
        exe = '"%s"' % sys.executable
    else:
        exe = sys.executable
    os.system('%s -c "import xml;print xml.__file__" >"%s"' % (exe, fnm))
    txt = open(fnm, 'r').read()[:-1]
    os.remove(fnm)
    if string.find(txt, '_xmlplus') > -1:
        if txt[:-3] == ".py":
            txt = txt + 'c'
        co = marshal.loads(open(txt, 'rb').read()[8:])
        mod.__init__('xml', txt, co)
    return mod
