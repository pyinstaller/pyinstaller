#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# This utility is primarily meant to be used when PyInstaller is not installed, e.g., to be run from a git checkout.

from PyInstaller.utils.cliutils.makespec import run

run()
