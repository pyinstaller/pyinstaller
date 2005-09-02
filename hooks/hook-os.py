import sys, string

def hook(mod):
    names = sys.builtin_module_names
    if 'posix' in names:
        removes = ['nt', 'ntpath', 'dos', 'dospath', 'os2', 'mac', 'macpath', 
                   'ce', 'riscos', 'riscospath', 'win32api', 'riscosenviron']
    elif 'nt' in names:
        removes = ['dos', 'dospath', 'os2', 'mac', 'macpath', 'ce', 'riscos', 
                   'riscospath', 'riscosenviron',]
    elif 'os2' in names:
        removes = ['nt', 'dos', 'dospath', 'mac', 'macpath', 'win32api', 'ce', 
                   'riscos', 'riscospath', 'riscosenviron',]
    elif 'dos' in names:
        removes = ['nt', 'ntpath', 'os2', 'mac', 'macpath', 'win32api', 'ce', 
                   'riscos', 'riscospath', 'riscosenviron',]
    elif 'mac' in names:
        removes = ['nt', 'ntpath', 'dos', 'dospath', 'os2', 'win32api', 'ce', 
                   'riscos', 'riscospath', 'riscosenviron',]
    for i in range(len(mod.imports)-1, -1, -1):
        nm = mod.imports[i][0]
        pos = string.find(nm, '.')
        if pos > -1:
            nm = nm[:pos]
        if nm in removes :
            del mod.imports[i]
    return mod

