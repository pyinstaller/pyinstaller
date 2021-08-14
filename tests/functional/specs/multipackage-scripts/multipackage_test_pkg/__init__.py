#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


def _test_basic_imports():
    # Import a very simple and rarely used pure-python lib ...
    import getopt  # noqa: F401
    # ... and a module importing a shared lib.
    import ssl  # noqa: F401

    print('Hello World!')


def _test_nested_data_file():
    # Try reading secret from a file in sub-directory.
    import os

    secret_file = os.path.join(__path__[0], 'data', 'secret.txt')
    print("Reading secret from %s..." % secret_file)
    with open(secret_file, 'r') as fp:
        secret = fp.read().strip()
    print("Secret: %s" % secret)

    assert secret == 'Secret1234'


def _test_nested_extensions():
    # Import psutil, which contains an extension in its package directory.
    import psutil  # noqa: F401
    print("Successfully imported psutil!")


def test_function():
    # Main test function
    _test_basic_imports()
    _test_nested_data_file()
    _test_nested_extensions()
