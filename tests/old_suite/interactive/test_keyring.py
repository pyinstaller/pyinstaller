# -----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------


import keyring


def main():
    keyring.set_password("pyinstaller", "username", "password")
    keyring.get_password("pyinstaller", "username")


if __name__ == '__main__':
    main()
