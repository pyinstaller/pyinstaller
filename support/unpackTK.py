import carchive
import sys
import os

this = carchive.CArchive(sys.executable)
tk = this.openEmbedded('tk.pkg')
targetdir = os.environ['_MEIPASS2']
for fnm in tk.contents():
    stuff = tk.extract(fnm)[1]
    outnm = os.path.join(targetdir, fnm)
    dirnm = os.path.dirname(outnm)
    if not os.path.exists(dirnm):
        os.makedirs(dirnm)
    open(outnm, 'wb').write(stuff)
tk = None

