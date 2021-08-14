# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Encode a string into utf8 bytestring and decode it back. The resulting string should match the original.

import codecs

str_a = 'foo bar fóó bář, fěě, ďěž'
str_a_utf8 = codecs.getencoder('utf-8')(str_a)[0]
str_b = codecs.getdecoder('utf-8')(str_a_utf8)[0]

print('codecs working: %s' % (str_a == str_b))
assert str_a == str_b
