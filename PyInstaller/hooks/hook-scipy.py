#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.


from distutils.version import LooseVersion
from PyInstaller.utils.hooks import hookutils

def hook(mod):
    # Current SciPy version string (e.g., "0.12.1").
    scipy_version = hookutils.exec_statement(
        'from scipy import version; print(version.short_version)')

    # SciPy < 0.14.0 uses SWIG to import dynamic libraries, which PyInstaller
    # has difficulty detecting. If the current SciPy is < 0.14.0,
    # unconditionally add all such libraries.
    if LooseVersion(scipy_version) < LooseVersion('0.14.0'):
        mod.add_binary(hookutils.collect_package_binaries('scipy'))

    return mod
