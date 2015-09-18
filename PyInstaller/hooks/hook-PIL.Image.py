#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import PyInstaller.utils.hooks as hookutils


def hook(mod):
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
        print(name)
""" % {'modname': mod.name}
    out = hookutils.exec_statement(statement)
    mod.add_import(out.strip().splitlines())

    # Ignore 'FixTk' to prevent inclusion of Tcl/Tk library.
    mod.del_import('FixTk')

    return mod
