#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Functional test exercising the default protocol `kwargs` of version 3 of the PyPubSub API.
"""

from wx.lib.pubsub import setupkwargs  # noqa: F401
from wx.lib.pubsub import pub as Publisher


def on_message(number):
    print('Message received.')
    if not number == 762:
        raise SystemExit('Message data "762" expected but received "%s".' % str(number))


Publisher.subscribe(on_message, 'topic.subtopic')
Publisher.sendMessage('topic.subtopic', number=762)
