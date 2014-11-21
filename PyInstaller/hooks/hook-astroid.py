#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
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

from hookutils import collect_data_files

# Note that brain/ isn't a module (it lacks an __init__.py, so it can't be
# referred to as astroid.brain; instead, locate it as package astriod,
# subdirectory brain/.
datas = collect_data_files('astroid', True, 'brain')
