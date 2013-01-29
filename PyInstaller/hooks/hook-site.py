#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Replace the code of real 'site' module by fake code doing nothing.

The real 'site' does some magic to find paths to other possible
Python modules. We do not want this behaviour for frozen applications.

Fake 'site' makes PyInstaller to work with distutils and to work inside
virtualenv environment.
"""


import os

import PyInstaller


def hook(mod):
    # Replace mod by fake 'site' module.
    pyi_dir = os.path.abspath(os.path.dirname(PyInstaller.__file__))
    fake_file = os.path.join(pyi_dir, 'fake', 'fake-site.py')
    new_code_object = PyInstaller.utils.misc.get_code_object(fake_file)
    mod = PyInstaller.depend.modules.PyModule('site', fake_file, new_code_object)
    return mod
