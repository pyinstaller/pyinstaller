#!/usr/bin/env bash
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
#
# This batch file ist used for testing running the cli-utls and script
# entrypoints from the command line. It' meant to test argument
# parsing.
#

set -e # exit on error

entrypoints="pyinstaller pyi-archive_viewer pyi-bindepend
             pyi-makespec"
# pyi-grab_version pyi-set_version are windows only
for ep in $entrypoints ; do
    echo -n $(which $ep )
    $ep --help > /dev/null
    rc=$?
    echo -e "\t--help result: $rc"
done

pyi-bindepend /usr/bin/sh
mkdir /tmp/pyitest
cd /tmp/pyitest

echo "import os" > test.py
pyi-makespec test.py > /dev/null
ls test.spec

pyinstaller test.py > /dev/null
pyi-archive_viewer -rb dist/test/test > /dev/null

