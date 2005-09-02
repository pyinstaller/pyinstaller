hiddenimports = ['xml.sax.xmlreader','xml.sax.expatreader']

def hook(mod):
    import os, tempfile, sys, string, marshal
    fnm = tempfile.mktemp()
    if string.find(sys.executable, ' ') > -1:
        exe = '"%s"' % sys.executable
    else:
        exe = sys.executable
    os.system('%s -c "import xml;print xml.__file__" >"%s"' % (exe, fnm))
    txt = open(fnm, 'r').read()[:-1]
    os.remove(fnm)
    if string.find(txt, '_xmlplus') > -1:
        if txt[:-3] == ".py":
            txt = txt + 'c'
        co = marshal.loads(open(txt, 'rb').read()[8:])
        mod.__init__('xml', txt, co)
    return mod
