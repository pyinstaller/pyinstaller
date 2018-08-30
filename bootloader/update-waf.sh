# -----------------------------------------------------------------------------
# Copyright (c) 2014-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------
#
# Helper-script for updating waf

VERSION=2.0.9
ARCHNAME=waf-$VERSION.tar.bz2
URL=https://waf.io/$ARCHNAME

# Extensions to include
TOOLS=--tools=cfg_cross_gnu

# Core tools to add: use only those we actually use
# Currently unused optimization
#c_compilers=clang,gcc,icc,msvc,suncc,xlc,ar
#c_tools=compiler_c,ccroot,c_config,c_aliases,c_preproc,c_config,c_osx,c_tests
#CORETOOLS=--coretools=$c_tools,$c_compilers

KEYID=49B4C67C05277AAA
KEYURL=https://raw.githubusercontent.com/waf-project/waf/master/utils/pubkey.asc


# remember where we come from
BASEDIR=$(pwd $(basename "$0"))

function cleanup () {
    cd "$BASEDIR"
    echo >&2 "Removing temporary directory '$WORKDIR'"
    rm -rf "$WORKDIR"
}

WORKDIR=$(mktemp -d)
trap cleanup SIGINT SIGTERM SIGKILL EXIT

cd $WORKDIR

# If Thomas Nagy's key is not already present, add it
gpg --list-keys 2>/dev/null | grep -cq $KEYID
if [ $? -ne 0 ] ; then
    echo "Adding Thomas Nagy's PGP key"
    wget --no-verbose $KEYURL
    gpg --import pubkey.asc
fi


echo "Downloading waf archive"
wget --no-verbose $URL
wget --no-verbose $URL.asc
echo

echo "Verifying archive signature"
gpg --verify $ARCHNAME.asc $ARCHNAME || exit 1

echo "Unpacking archive"
tar xjf $ARCHNAME
cd waf-$VERSION

echo "Building new waf file"
./waf-light $CORETOOLS $TOOLS

cp -v ./waf "$BASEDIR"
