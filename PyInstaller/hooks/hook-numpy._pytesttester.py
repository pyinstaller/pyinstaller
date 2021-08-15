# -----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

# numpy._pytesttester is unconditionally imported by numpy.core, thus we can not exclude _pytesttester (which would be
# preferred). Anway, we can avoid importing pytest, which pulls in anotehr 150+ modules. See
# https://github.com/numpy/numpy/issues/17183

excludedimports = ["pytest"]
