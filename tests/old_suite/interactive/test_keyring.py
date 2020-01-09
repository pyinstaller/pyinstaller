# -----------------------------------------------------------------------------
# Copyright (c) 2014-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------


import keyring


def main():
    keyring.set_password("pyinstaller", "username", "password")
    keyring.get_password("pyinstaller", "username")


if __name__ == '__main__':
    main()
