#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
