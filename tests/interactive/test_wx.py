# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import wx


def main():

    def onKeyDown(event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            frame.Close()

    app = wx.App(0)
    frame = wx.Frame(None, title="Hello World from wxPython")
    panel = wx.Panel(frame)
    label = wx.StaticText(panel, -1,
                          u"Press <ESC> to exit. Some non-ascii chars: řčšěíáŘ")
    panel.Bind(wx.EVT_KEY_DOWN, onKeyDown)
    panel.SetFocus()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
