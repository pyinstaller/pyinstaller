#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


attrs = [('notamodule','')]

# Replace package `pkg1` the code and content of `pkg2`, while the
# name `pkg1` is kept. `pkg2` is not contained in the fozen exe.
# See test_pkg_structures.py for more details.

def hook(mod):
    import os
    # TODO This does not work with modulegraph yet, submodules are not
    # included.
    pkg2_path = os.path.normpath(os.path.join(mod.__path__[0], '../pkg2'))
    mod.retarget(os.path.join(pkg2_path, '__init__.py'))
    mod.__path__ = [pkg2_path, os.path.join(pkg2_path, 'extra')]
    mod.node.packagepath = mod.__path__
    mod.del_import('pkg2')
    return mod
