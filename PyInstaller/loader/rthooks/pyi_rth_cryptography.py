# -----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

# Originally from Stack Overflow

from cryptography.hazmat import backends

try:
    from cryptography.hazmat.backends.commoncrypto.backend import backend as be_cc
except ImportError:
    be_cc = None

try:
    from cryptography.hazmat.backends.openssl.backend import backend as be_ossl
except ImportError:
    be_ossl = None

backends._available_backends_list = [
    be for be in (be_cc, be_ossl) if be is not None
    ]
