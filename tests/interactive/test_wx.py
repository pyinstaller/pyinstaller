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
    app = wx.App(0)
    frame = wx.Frame(None, title="Hello World from wxPython")
    panel = wx.Panel(frame)
    label = wx.StaticText(panel, -1, "Hello World from wxPython")
    frame.Fit()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
