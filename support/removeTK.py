import sys, os

def empty(dir):
    try:
        fnms = os.listdir(dir)
    except OSError:
        return
    for fnm in fnms:
        path = os.path.join(dir, fnm)
        if os.path.isdir(path):
            empty(path)
            try:
                os.rmdir(path)
            except:
                pass
        else:
            try:
                os.remove(path)
            except:
                pass

tcldir = os.environ['TCL_LIBRARY']
prvtdir = os.path.dirname(tcldir)
if os.path.basename(prvtdir) == '_MEI':
    empty(prvtdir)
    os.rmdir(prvtdir)

