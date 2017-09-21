#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import eval_statement

### This basically is a copy of pre_safe_import_module/hook-six.moves.py
### adopted to urllib3.packages.six.
### Please see pre_safe_import_module/hook-six.moves.py for documentation.

def pre_safe_import_module(api):
    real_to_six_module_name = eval_statement(
'''
import urllib3.packages.six as six
print('{')

for moved in six._moved_attributes:
    if isinstance(moved, (six.MovedModule, six.MovedAttribute)):
        print('  %r: %r,' % (
            moved.mod,
            'urllib3.packages.six.moves.' + moved.name))

print('}')
''')
    api.add_runtime_package(api.module_name)
    for real_module_name, six_module_name in real_to_six_module_name.items():
        api.add_alias_module(real_module_name, six_module_name)
