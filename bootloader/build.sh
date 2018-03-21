#!/bin/bash
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

if [ ! -r "_sdks/osx/osxcross.tar.xz" ] ; then
	echo "Building the OS X SDK and cctools"
	vagrant up --no-provision build-osxcross
	vagrant provision build-osxcross
	vagrant destroy builx-osxcross
	echo
fi

# start the build-guests
vagrant up --no-provision linux64 windows10

# build the bootloaders
vagrant provision linux64            # GNU/Linux bootloaders
TARGET=OSX vagrant provision linux64 # OS X bootloaders
vagrant provision windows10          # Windows bootloaders (using msvc)

# verify the bootloaders have been built
git status ../PyInstaller/bootloader/

read -n 1 -p "Destroy or shutdown machines? (D/s/n) " REPLY
echo
REPLY=${REPLY^^*}
if [ "$REPLY" = "D" ] ; then
	echo
	vagrant destroy -f linux64 windows10
elif [ "${REPLY,,*}" = "s" ] ; then
	echo
	vagrant halt linux64 windows10
elif [ "${REPLY,,*}" != "n" ] ; then
	echo "Invalid answer. You may halt the machines manually using 'vagrant halt linux64  windows10'"
fi
