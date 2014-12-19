#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from wx.lib.pubsub import setuparg1
from wx.lib.pubsub import pub as Publisher


def on_message(message):
    print("In the handler")
    # Data is delivered encapsulated in message and
    # not directly as function argument.
    if not message.data == 762:
        raise SystemExit('wx_pubsub_arg1 failed.')


Publisher.subscribe(on_message, 'topic.subtopic')
Publisher.sendMessage('topic.subtopic', 762)
