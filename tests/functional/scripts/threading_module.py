#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import threading


def doit(nm):
    print(('%s started' % nm))
    import pyi_testmod_threading
    print(('%s %s' % (nm, pyi_testmod_threading.x)))


t1 = threading.Thread(target=doit, args=('t1',))
t2 = threading.Thread(target=doit, args=('t2',))
t1.start()
t2.start()
doit('main')
t1.join()
t2.join()
