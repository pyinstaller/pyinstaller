#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This hook was tested with Pillow 2.9.0 (Maintained fork of PIL):
# https://pypi.python.org/pypi/Pillow

from PyInstaller.compat import modname_tkinter
from PyInstaller.utils.hooks import collect_submodules


# Ignore 'FixTk' (Python 2) or tkinter to prevent inclusion of Tcl/Tk library.
# Assume that if people are really using tkinter in their application, they
# will also import it directly.
excludedimports = [modname_tkinter, 'FixTk']
# Include all PIL image plugins - module names containing 'ImagePlugin'.
# e.g.  PIL.JpegImagePlugin
hiddenimports = collect_submodules('PIL', pattern='ImagePlugin')


# def hook(mod):
#     # `PIL.Image` may be imported as `PIL.Image` or as `Image`
#     # (without the prefix). We need to use the same module name to
#     # avoid the same module under two different names.
#     # We cannot import modules directly in PyInstaller.
#     statement = """
# import sys
# __import__('%(modname)s')
# image_mod = sys.modules['%(modname)s']
# # PIL uses lazy initialization.
# # first import the default stuff ...
# image_mod.preinit()
# # ... then every available plugin
# image_mod.init()
# for name in sys.modules:
#     if name.endswith('ImagePlugin'):
#         # Modules are printed to stdout and the output is then parsed.
#         print(name)
# """ % {'modname': mod.name}
#     out = hookutils.exec_statement(statement)
#     mod.add_import(out.strip().splitlines())
#
#     mod.del_import('FixTk')
#
#     return mod
