# -*- coding: utf-8 ; mode: python -*-
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

import os
import sys

# To verify that the bootloader actually uses the unresolved symlink basename when executing the second process,
# check what the `Name:` entry in '/proc/self/status' says. This value is truncated to 15 characters.
#
# This test is run twice: once with a short basename and once with a long basename, in order to detect if this
# 15-character limit is no longer true.

with open('/proc/self/status', 'r') as fh:
    for line in fh.readlines():
        if line.startswith('Name:'):
            name_from_proc = line.split(":")[1].strip()
            break

name_from_argv = os.path.basename(sys.argv[0])
# linux will truncate the name to 15 chars
truncated_name_from_argv = name_from_argv[:15]

print('ARGV:', repr(name_from_argv), "(complete)")
print('ARGV:', repr(truncated_name_from_argv), "(truncated")
print('PROC:', repr(name_from_proc))
assert truncated_name_from_argv == name_from_proc
