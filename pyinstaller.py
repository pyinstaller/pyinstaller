#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This utility is primary meant to be used when PyInstaller is not
# installed, eg. when be run by a git checkout.

from PyInstaller.__main__ import run
run()
