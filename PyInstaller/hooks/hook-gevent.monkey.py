#-----------------------------------------------------------------------------
# Copyright (c) 2015-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# gevent is a coroutine -based Python networking library that uses greenlet to
# provide a high-level synchronous API on top of the libev event loop.
#
# http://www.gevent.org/
#
# Tested with gevent 1.0.2 and 1.1b6

from PyInstaller.utils.hooks import is_module_satisfies

# monkey patching in gevent 1.1 uses dynamic imports
if is_module_satisfies('gevent >= 1.1b0'):
    hiddenimports = [
        'gevent.builtins',
        'gevent.os',
        'gevent.select',
        'gevent.signal',
        'gevent.socket',
        'gevent.subprocess',
        'gevent.ssl',
        'gevent.thread',
        'gevent.threading'
    ]
