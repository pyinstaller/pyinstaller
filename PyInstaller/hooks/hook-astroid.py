#-----------------------------------------------------------------------------
# Copyright (c) 2014-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# ***************************************************
# hook-astriod.py - PyInstaller hook file for astriod
# ***************************************************
# The astriod package, in __pkginfo__.py, is version 1.1.1. Looking at its
# source:
#
# From __init__.py, starting at line 111::
#
#    BRAIN_MODULES_DIR = join(dirname(__file__), 'brain')
#    if BRAIN_MODULES_DIR not in sys.path:
#        # add it to the end of the list so user path take precedence
#        sys.path.append(BRAIN_MODULES_DIR)
#    # load modules in this directory
#    for module in listdir(BRAIN_MODULES_DIR):
#        if module.endswith('.py'):
#            __import__(module[:-3])
#
# So, we need all the Python source in the ``brain/`` subdirectory,
# since this is run-time discovered and loaded. Therefore, these
# files are all data files.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, \
    is_module_or_submodule

# Note that brain/ isn't a module (it lacks an __init__.py, so it can't be
# referred to as astroid.brain; instead, locate it as package astriod,
# subdirectory brain/.
datas = collect_data_files('astroid', True, 'brain')

# Update: in astroid v 1.4.1, the brain/ module import parts of astroid. Since
# everything in brain/ is dynamically imported, these are hidden imports. For
# simplicity, include everything in astroid. Exclude all the test/ subpackage
# contents and the test_util module.
hiddenimports = collect_submodules('astroid',
  lambda name: (not is_module_or_submodule(name, 'astroid.tests')) and
               (not name == 'test_util'))
