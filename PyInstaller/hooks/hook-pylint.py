#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# *************************************************
# hook-pylint.py - PyInstaller hook file for pylint
# *************************************************
# The pylint package, in __pkginfo__.py, is version 1.4.3. Looking at its
# source:
#
# From checkers/__init__.py, starting at line 122::
#
#    def initialize(linter):
#        """initialize linter with checkers in this package """
#        register_plugins(linter, __path__[0])
#
# From reporters/__init__.py, starting at line 131::
#
#    def initialize(linter):
#        """initialize linter with reporters in this package """
#        utils.register_plugins(linter, __path__[0])
#
# From utils.py, starting at line 881::
#
#    def register_plugins(linter, directory):
#        """load all module and package in the given directory, looking for a
#        'register' function in each one, used to register pylint checkers
#        """
#        imported = {}
#        for filename in os.listdir(directory):
#            base, extension = splitext(filename)
#            if base in imported or base == '__pycache__':
#                continue
#            if extension in PY_EXTS and base != '__init__' or (
#                 not extension and isdir(join(directory, base))):
#                try:
#                    module = load_module_from_file(join(directory, filename))
#
#
# So, we need all the Python source in the ``checkers/`` and ``reporters/``
# subdirectories, since these are run-time discovered and loaded. Therefore,
# these files are all data files. In addition, since this is a module, the
# pylint/__init__.py file must be included, since submodules must be children of
# a module.

from PyInstaller.utils.hooks import collect_data_files
import pylint

datas = (
         [(pylint.__file__, 'pylint')] +
         collect_data_files('pylint.checkers', True) +
         collect_data_files('pylint.reporters', True)
         )
