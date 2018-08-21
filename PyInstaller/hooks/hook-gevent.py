#-----------------------------------------------------------------------------
# Copyright (c) 2015-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
#
# Import hook for gevent https://github.com/gevent/gevent
# partialy tested with gevent 1.3.1

hiddenimports = [
        'gevent.__greenlet_primitives',
        'gevent.__hub_local',
        'gevent.__hub_primitives',
        'gevent.__ident',
        'gevent.__imap',
        'gevent.__semaphore',
        'gevent.__tracer',
        'gevent.__waiter',
        'gevent._event',
        'gevent._greenlet',
        'gevent._local',
        'gevent._queue',

        # info steal from gevent.monkey patch_all() args
        'gevent.os',
        'gevent.time',
        'gevent.thread',
        # 'gevent.sys',
        'gevent.socket',
        'gevent.select',
        'gevent.ssl',
        # 'gevent.httplib',
        'gevent.subprocess',
        'gevent.builtins',
        'gevent.signal',

        'gevent.libev',
        'gevent.libev.corecext',
        'gevent.libev.corecffi',
        'gevent.libev.watcher',

        'gevent.libuv',
        'gevent.libuv._corecffi',
        'gevent.libuv.loop',
        'gevent.libuv.watcher',
    ]

