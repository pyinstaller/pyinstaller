#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Compare attributes of ElementTree (cElementTree) module from frozen executable with ElementTree (cElementTree)
# module from standard python.

import copy
import os
import subprocess
import xml.etree.ElementTree as ET
import xml.etree.cElementTree as cET

from pyi_testmod_gettemp import gettemp

_pyexe_file = gettemp("python_exe.build")

with open(_pyexe_file) as fp:
    _lines = fp.readlines()
    _pyexe = _lines[0].strip()
    _env_path = _lines[2].strip()


def exec_python(pycode):
    """
    Wrap running python script in a subprocess.

    Return stdout of the invoked command.
    """
    # Environment variable 'PATH' has to be defined on Windows, otherwise dynamic library pythonXY.dll cannot be
    # found by the Python executable.
    env = copy.deepcopy(os.environ)
    env['PATH'] = _env_path
    out = subprocess.Popen([_pyexe, '-c', pycode], env=env, stdout=subprocess.PIPE, shell=False).stdout.read()
    # In Python 3, stdout is a byte array and must be converted to string.
    out = out.decode('ascii').strip()

    return out


def compare(test_name, expect, frozen):
    # Modules in Python 3 contain attr '__cached__' - add it to the frozen list.
    if '__cached__' not in frozen:
        frozen.append('__cached__')
    frozen.sort()
    frozen = str(frozen)

    print(test_name)
    print('  Attributes expected: ' + expect)
    print('  Attributes current:  ' + frozen)
    print('')
    # Compare attributes of frozen module with unfronzen module.
    if not frozen == expect:
        raise SystemExit('Frozen module has no same attributes as unfrozen.')


# General Python code for subprocess.
subproc_code = """
import {0} as myobject
lst = dir(myobject)
# Sort attributes.
lst.sort()
print(lst)
"""

# Pure Python module.
_expect = exec_python(subproc_code.format('xml.etree.ElementTree'))
_frozen = dir(ET)
compare('ElementTree', _expect, _frozen)

# C-extension Python module.
_expect = exec_python(subproc_code.format('xml.etree.cElementTree'))
_frozen = dir(cET)
compare('cElementTree', _expect, _frozen)
