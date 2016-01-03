#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional test exercising PyPubSub's default protocol.

The default protocol conditionally depends on the current wxPython version. If:

* **wxPython 2.8** or older is available, the default protocol is version 1
  (referred to elsewhere as either `pubsub1` or `v1`).
* **wxPython 2.9** or newer is available, the default protocol is the version 3
  `kwargs` protocol.

Hence, this test is identical to explicitly importing the setup package for the
default protocol specific to the current wxPython version (e.g., `setupv1` for
wxPython 2.8 or older) _before_ the existing import from `wx.lib.pubsub` below.


NOTE: "wx.lib.pubsub.__init__" on 2.8 tries to use `imp.find_loader`
to find out if the module is importable; because `imp.find_loader` does not honor
our FrozenImporter path hook, it always returns None for *any* frozen module. This
means 2.8 never uses the v1 API when frozen, a deviation from its non-frozen behavior.

We work around this in the wx.lib.pubsub hook by including `autosetuppubsubv1.py`
as a data file instead of a python module, which stores it as a plain file in the
exe folder (or temp folder) and makes it visible to `imp.find_loader`.
"""

# Attempt to import the placeholder "wx.lib.pubsub.autosetuppubsubv1" module.
# We can't use `find_loader` to locate it because it may be present on both
# wxPython 2.8 and 2.9; version 2.9 explicitly raises ImportError to
# pretend it is not found. For whatever reason.
#
# Importing this module has no side effects; it either raises ImportError
# or does nothing.
try:
    import wx.lib.pubsub.autosetuppubsubv1
# If that failed, the current version of wxPython is 2.9 or newer, in which case
# the default protocol is the version 3 "kwargs" protocol.
except ImportError:
    from wx.lib.pubsub import pub as Publisher
    print('wxPython 2.9 or newer detected.')

    def on_message(number):
        print('Message received.')
        if not number == 762:
            raise SystemExit(
                'Message data "762" expected but received "%s".' % str(number))

    Publisher.subscribe(on_message, 'topic.subtopic')
    Publisher.sendMessage('topic.subtopic', number=762)
# Else that succeeded, implying the current version of wxPython to be 2.8 or
# older, in which case the default protocol is the version 1 protocol. For
# details on why this works, see "wx.lib.pubsub.__init__" in wxPython 2.8.
else:
    from wx.lib.pubsub import Publisher
    print('wxPython 2.8 or older detected.')

    def on_message(message):
        print('Message received.')
        if not message.data == 762:
            raise SystemExit(
                'Message data "762" expected but received "%s".' % str(message.data))

    Publisher.subscribe(on_message, 'topic.subtopic')
    Publisher.sendMessage('topic.subtopic', 762)
