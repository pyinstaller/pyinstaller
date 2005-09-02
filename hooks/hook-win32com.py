import os

def hook(mod):
    pth = str(mod.__path__[0])
    if os.path.isdir(pth):
        mod.__path__.append(
            os.path.normpath(os.path.join(pth, '../win32comext')))
    return mod
