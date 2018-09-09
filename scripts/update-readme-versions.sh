#!/bin/sh
#
# This script updates the version within the README file.
#
# - Change version in the badge-images and related links
#

VERSION="$1"

if [ -z "$VERSION" ] ; then
    echo "Requires a version number"
    exit 10
fi

INFILE="$(dirname "$0")/../README.rst"

sed -e '/pyinstaller\.readthedocs\.io\// s!/latest!/v'$VERSION'!' \
    -i "$INFILE"
