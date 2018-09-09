#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import eval_statement

### This basically is a copy of pre_safe_import_module/hook-six.moves.py
### adopted to setuptools.extern.six resp. setuptools._vendor.six.
### Please see pre_safe_import_module/hook-six.moves.py for documentation.

# Note that the moves are defined in 'setuptools._vendor.six' but are imported
# under 'setuptools.extern.six'.

def pre_safe_import_module(api):
    real_to_six_module_name = eval_statement(
'''
import setuptools._vendor.six as six
print('{')

for moved in six._moved_attributes:
    if isinstance(moved, (six.MovedModule, six.MovedAttribute)):
        print('  %r: %r,' % (
            moved.mod,
            'setuptools.extern.six.moves.' + moved.name))

print('}')
''')
    api.add_runtime_package(api.module_name)
    for real_module_name, six_module_name in real_to_six_module_name.items():
        api.add_alias_module(real_module_name, six_module_name)
