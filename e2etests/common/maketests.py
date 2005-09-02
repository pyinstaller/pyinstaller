import sys, string, os
if sys.platform[:3] == 'win':
    stripopts = ('',)
    consoleopts = ('', '--noconsole')
else:
    stripopts = ('', '--strip')
    consoleopts = ('',)
if string.find(sys.executable, ' ') > -1:
    exe = '"%s"' % sys.executable
else:
    exe = sys.executable
if sys.platform[:3] == 'win':
    spec = "%s ../../Makespec.py --tk %%s %%s %%s %%s %%s --out t%%d hanoi.py" % exe
    bld = "%s ../../Build.py t%%d/hanoi.spec" % exe
else:
    spec = "%s ../../Makespec.py --tk %%s %%s %%s %%s %%s --out /u/temp/t%%d hanoi.py" % exe
    bld = "%s ../../Build.py /u/temp/t%%d/hanoi.spec" % exe

i = 0
for bldconfig in ('--onedir', '--onefile'):
    for console in consoleopts:
        for dbg in ('--debug', ''):
            for stripopt in stripopts:
                for upxopt in ('', '--upx'):
                    cmd = spec % (bldconfig, console, dbg, stripopt, upxopt, i)
                    os.system(cmd)
                    os.system(bld % i)
                    if sys.platform[:5] == 'linux':
                        if bldconfig == '--onedir':
                            os.system("ln -s /u/temp/t%d/disthanoi/hanoi hanoi%d" % (i,i))
                        else:
                            os.system("ln -s /u/temp/t%d/hanoi hanoi%d" % (i,i))
                    i += 1
            
