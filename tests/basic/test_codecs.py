#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import codecs
import sys


a = 'foo bar'
au = codecs.getdecoder('utf-8')(a)[0]
b = codecs.getencoder('utf-8')(au)[0]


print('codecs working: %s' % (a == b))
assert a == b


sys.exit(0)
