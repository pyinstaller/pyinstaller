#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['xml.sax.xmlreader','xml.sax.expatreader']

def hook(mod):
    # This hook checks for the infamous _xmlcore hack
    # http://www.amk.ca/diary/2003/03/pythons__xmlplus_hack.html

    from hookutils import exec_statement
    import marshal

    txt = exec_statement("import xml;print xml.__file__")

    if txt.find('_xmlplus') > -1:
        if txt.endswith(".py"):
            txt = txt + 'c'
        try:
            co = marshal.loads(open(txt, 'rb').read()[8:])
        except IOError:
            co = compile(open(txt[:-1], 'rU').read(), txt, 'exec')
        old_pth = mod.__path__[:]
        mod.__init__('xml', txt, co)
        mod.__path__.extend(old_pth)
    return mod
