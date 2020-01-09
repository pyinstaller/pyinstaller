#-----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Hook for https://github.com/PyWavelets/pywt

hiddenimports = ['pywt._extensions._cwt']

# NOTE: There is another project `https://github.com/Knapstad/pywt installing
# a packagre `pywt`, too. This name clash is not much of a problem, even if
# this hook is picked up for the other package, since PyInstaller will simply
# skip any module added by this hook but acutally missing. If the other project
# requires a hook, too, simply add it to this file.
