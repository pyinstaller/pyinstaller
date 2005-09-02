hiddenimports = ['win32com.server.policy']

def hook(mod):
    import sys
    if hasattr(sys, 'version_info'):
        vers = '%d%d' % (sys.version_info[0], sys.version_info[1])
    else:
        import string
        toks = string.split(sys.version[:3], '.')
        vers = '%s%s' % (toks[0], toks[1])
    newname = 'pythoncom%s' % vers
    if mod.typ == 'EXTENSION':
        mod.__name__ = newname
    else:
        import win32api
        h = win32api.LoadLibrary(newname+'.dll')
        pth = win32api.GetModuleFileName(h)
        #win32api.FreeLibrary(h)
        import mf
        mod = mf.ExtensionModule(newname, pth)
    return mod

