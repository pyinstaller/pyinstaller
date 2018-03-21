#!/bin/bash
#
# Copyright (c) 2005-2018, PyInstaller Development Team.
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

