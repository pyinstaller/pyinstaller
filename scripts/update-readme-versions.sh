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

sed -e '/img\.shields\.io.*travis/   s/\<develop\>/'$VERSION'/' \
    -e '/img\.shields\.io.*appveyor/ s/\<develop\>/'$VERSION'/' \
    -e '/ci\.appveyor/  s/\<develop\>/'$VERSION'/' \
    -e '/landscape\.io/ s/\<develop\>/master/' \
    -e '/img\.shields\.io\/badge\// s/-latest-/-v'$VERSION'-/' \
    -e '/pyinstaller\.rtfd\.io\// s/\<latest\>/v'$VERSION'/' \
    -i "$INFILE"
