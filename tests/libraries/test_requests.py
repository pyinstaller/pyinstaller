# -----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

import requests


def main():
    # Need to load an HTTPS website to test the self-signed cert
    requests.get('https://github.com')


if __name__ == '__main__':
    main()
