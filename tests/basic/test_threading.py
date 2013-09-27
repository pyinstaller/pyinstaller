#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import threading


def doit(nm):
    print('%s started' % nm)
    import data7
    print('%s %s' % (nm, data7.x))


t1 = threading.Thread(target=doit, args=('t1',))
t2 = threading.Thread(target=doit, args=('t2',))
t1.start()
t2.start()
doit('main')
t1.join()
t2.join()
