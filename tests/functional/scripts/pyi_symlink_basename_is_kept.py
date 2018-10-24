# -*- coding: utf-8 ; mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

with open('/proc/self/status', 'r') as fh:
    for line in fh.readlines():
        if line.startswith('Name:'):
            name_from_proc = line.split(":")[1].strip()
            break

# PyInstaller bootloader assumes the `Name:` entry in '/proc/self/status' to
# be truncated to 15 characters. Fail if this assumption is no longer true.

name_from_argv = os.path.basename(sys.argv[0])
# linux will truncate the name to 15 chars
truncated_name_from_argv = name_from_argv[:15]

print('ARGV:', repr(truncated_name_from_argv))
print('PROC:', repr(name_from_proc))
assert truncated_name_from_argv == name_from_proc
