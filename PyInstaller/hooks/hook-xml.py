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
    # This hook checks for the infamous _xmlcore hack
    # http://www.amk.ca/diary/2003/03/pythons__xmlplus_hack.html

    from hookutils import exec_statement
    import marshal

    txt = exec_statement("import xml;print xml.__file__")

    if txt.find('_xmlplus') > -1:
        if txt.endswith(".py"):
            txt = txt + 'c'
        co = marshal.loads(open(txt, 'rb').read()[8:])
        old_pth = mod.__path__[:]
        mod.__init__('xml', txt, co)
        mod.__path__.extend(old_pth)
    return mod
