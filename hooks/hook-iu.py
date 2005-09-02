import sys, string

def hook(mod):
    names = sys.builtin_module_names
    if 'posix' in names:
        removes = ['nt', 'dos', 'os2', 'mac', 'win32api']
    elif 'nt' in names:
        removes = ['dos', 'os2', 'mac']
    elif 'os2' in names:
        removes = ['nt', 'dos', 'mac', 'win32api']
    elif 'dos' in names:
        removes = ['nt', 'os2', 'mac', 'win32api']
    elif 'mac' in names:
        removes = ['nt', 'dos', 'os2', 'win32api']
    for i in range(len(mod.imports)-1, -1, -1):
        nm = mod.imports[i][0]
        pos = string.find(nm, '.')
        if pos > -1:
            nm = nm[:pos]
        if nm in removes:
            del mod.imports[i]
    return mod

