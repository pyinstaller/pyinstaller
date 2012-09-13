#
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


from PyInstaller.hooks import hookutils


hiddenimports = []


def hook(mod):
    global hiddenimports
    # `PIL.Image` may be imported as `PIL.Image` or as `Image`
    # (without the prefix). We need to use the same module name to
    # avoid the same module under two different names.
    # We cannot import modules directly in PyInstaller.
    statement = """
import sys
__import__('%(modname)s')
image_mod = sys.modules['%(modname)s']
# PIL uses lazy initialization.
# first import the default stuff ...
image_mod.preinit()
# ... then every available plugin
image_mod.init()
for name in sys.modules:
    if name.endswith('ImagePlugin'):
        # Modules are printed to stdout and the output is then parsed.
        print name
""" % {'modname': mod.__name__}
    out = hookutils.exec_statement(statement)
    hiddenimports = out.strip().splitlines()
    # Ignore 'FixTk' to prevent inclusion of Tcl/Tk library.
    for i, m in enumerate(mod.imports):
        if m[0] == 'FixTk':
            del mod.imports[i]
            break
    return mod
