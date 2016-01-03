#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional test exercising the default protocol `kwargs` of version 3 of the
PyPubSub API.
"""

from wx.lib.pubsub import setupkwargs
from wx.lib.pubsub import pub as Publisher

def on_message(number):
    print('Message received.')
    if not number == 762:
        raise SystemExit(
            'Message data "762" expected but received "%s".' % str(number))

Publisher.subscribe(on_message, 'topic.subtopic')
Publisher.sendMessage('topic.subtopic', number=762)
