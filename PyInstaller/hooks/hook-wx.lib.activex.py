from PyInstaller.hooks.hookutils import exec_statement
exec_statement("import wx.lib.activex") #this needed because comtypes wx.lib.activex generates some stuff
