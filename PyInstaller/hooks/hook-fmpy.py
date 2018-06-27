#-----------------------------------------------------------------------------
# Copyright (c) 2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for FMPy, a library to simulate Functional Mockup Units (FMUs)
https://github.com/CATIA-Systems/FMPy

Adds the data files that are required at runtime:

- XSD schema files
- dynamic libraries for the CVode solver
- source and header files for the compilation of c-code FMUs
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('fmpy')
