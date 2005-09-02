import os, sys, iu, imp
class Win32ImportDirector(iu.ImportDirector):
    def __init__(self):
        self.path = sys.path[0] # since I run as a hook, sys.path probably hasn't been mucked with
        if hasattr(sys, 'version_info'):
            self.suffix = '%d%d'%(sys.version_info[0],sys.version_info[1])
        else:
            self.suffix = '%s%s' % (sys.version[0], sys.version[2])
    def getmod(self, nm):
        fnm = os.path.join(self.path, nm+self.suffix+'.dll')
        try:
            fp = open(fnm, 'rb')
        except:
            return None
        else:
            mod = imp.load_module(nm, fp, fnm, ('.dll', 'rb', imp.C_EXTENSION))
            mod.__file__ = fnm
            return mod
sys.importManager.metapath.insert(1, Win32ImportDirector())