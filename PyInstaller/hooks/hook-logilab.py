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
# hook-logilab.py - PyInstaller hook file for logilab
# ***************************************************
# The logilab package, in common/__pkginfo__.py, is version 0.63.2. Looking at
# its source:
#
# From common/configuration.py, starting at line 126::
#
#     from six.moves import range, configparser as cp, input
#
# The six module does run-time imports of all its moved modules.
# So. The range module is found elsewhere, but configparser
# (which is named ConfigParser in Python 2.7) is not. So, mark
# it as a hidden import.
#
# From astng/__init__.py, starting at line 72::
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
# So, we need files from the ``brain/`` subdirectory as well.
#
# Note: this only seems to affect Unix; however, it seems like
# it might apply to other platforms as well, so the hidden import
# below applies to all platforms. In addition, since this is a module, the
# __init__.py file must be included, since submodules must be children of
# a module.

from hookutils import collect_data_files
import logilab

hiddenimports = ['ConfigParser']

# Note that brain/ isn't a module (it lacks an __init__.py, so it can't be
# referred to as logilab.brain; instead, locate it as package logilab,
# subdirectory brain/.
datas = (
         [(logilab.__file__, 'logilab')] +
         collect_data_files('logilab.astng', True, 'brain')
         )
