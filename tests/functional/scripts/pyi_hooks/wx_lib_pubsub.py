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
Functional test exercising PyPubSub's default protocol.

The default protocol conditionally depends on the current wxPython version. If:

* **wxPython 2.8** or older is available, the default protocol is version 1 (referred to as either `pubsub1` or `v1`).
* **wxPython 2.9** or newer is available, the default protocol is the version 3 `kwargs` protocol.

Hence, this test is identical to explicitly importing the setup package for the default protocol, specific to the
current wxPython version (e.g., `setupv1` for wxPython 2.8 or older) _before_ the existing import from
`wx.lib.pubsub` below.


NOTE: "wx.lib.pubsub.__init__" on 2.8 tries to use `imp.find_loader` to find out if the module is importable;
because `imp.find_loader` does not honor our FrozenImporter path hook, it always returns None for *any* frozen module.
This means that 2.8 never uses the v1 API when frozen, which is a deviation from its non-frozen behavior.

We work around this in the wx.lib.pubsub hook by including the `autosetuppubsubv1.py` as a data file instead of a
python module, which stores it as a plain file in the exe folder (or temp folder) and thus makes it visible
to the `imp.find_loader`.
"""

# Attempt to import the placeholder "wx.lib.pubsub.autosetuppubsubv1" module.
# We cannot use the `find_loader` to locate it, because it may be present on both wxPython 2.8 and 2.9;
# version 2.9 explicitly raises ImportError to pretend it is not found. For whatever reason.
#
# Importing this module has no side effects; it either raises ImportError or does nothing.
try:
    import wx.lib.pubsub.autosetuppubsubv1  # noqa: F401
# Import failed, meaning that the current version of wxPython is 2.9 or newer, in which case the default protocol
# is the version 3 "kwargs" protocol.
except ImportError:
    from wx.lib.pubsub import pub as Publisher
    print('wxPython 2.9 or newer detected.')

    def on_message(number):
        print('Message received.')
        if not number == 762:
            raise SystemExit('Message data "762" expected but received "%s".' % str(number))

    Publisher.subscribe(on_message, 'topic.subtopic')
    Publisher.sendMessage('topic.subtopic', number=762)
# Import succeeded, implying that the current version of wxPython is 2.8 or older, in which case the default protocol
# is the version 1 protocol. For details on why this works, see "wx.lib.pubsub.__init__" in wxPython 2.8.
else:
    from wx.lib.pubsub import Publisher
    print('wxPython 2.8 or older detected.')

    def on_message(message):
        print('Message received.')
        if not message.data == 762:
            raise SystemExit('Message data "762" expected but received "%s".' % str(message.data))

    Publisher.subscribe(on_message, 'topic.subtopic')
    Publisher.sendMessage('topic.subtopic', 762)
