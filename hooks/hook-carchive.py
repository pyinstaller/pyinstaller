import sys

def hook(mod):
    if sys.version[0] > '1':
        for i in range(len(mod.imports)-1, -1, -1):
            if mod.imports[i][0] == 'strop':
                del mod.imports[i]
    return mod

