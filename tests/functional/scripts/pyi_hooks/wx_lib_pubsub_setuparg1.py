#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional test exercising the non-default protocol `arg1` of version 3 of the
PyPubSub API.
"""

from wx.lib.pubsub import setuparg1
from wx.lib.pubsub import pub as Publisher

def on_message(message):
    print('Message received.')
    if not message.data == 762:
        raise SystemExit(
            'Message data "762" expected but received "%s".' % str(message.data))

Publisher.subscribe(on_message, 'topic.subtopic')
Publisher.sendMessage('topic.subtopic', 762)
