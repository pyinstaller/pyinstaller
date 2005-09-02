import os, sys, glob, string
try:
    here=os.path.dirname(__file__)
except NameError:
    here=os.path.dirname(sys.argv[0])
PYTHON = sys.executable
if sys.platform[:3] == 'win':
    if string.find(PYTHON, ' ') > -1:
        PYTHON="%s" % PYTHON

def empty(dir):
    for fnm in os.listdir(dir):
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
    
def clean():
    distdirs = glob.glob(os.path.join(here, 'disttest*'))
    for dir in distdirs:
        try:
            empty(dir)
            os.rmdir(dir)
        except OSError, e:
            print e
    builddirs = glob.glob(os.path.join(here, 'buildtest*'))
    for dir in builddirs:
        try:
            empty(dir)
            os.rmdir(dir)
        except OSError, e:
            print e
    wfiles = glob.glob(os.path.join(here, 'warn*.txt'))
    for file in wfiles:
        try:
            os.remove(file)
        except OSError, e:
            print e
def runtests():
    specs = glob.glob(os.path.join(here, 'test*.spec'))
    for spec in specs:
        print
        print "Running %s" % spec
        print
        test = os.path.splitext(os.path.basename(spec))[0]
        os.system('%s ../Build.py %s' % (PYTHON, spec))
        os.system('dist%s%s%s.exe' % (test, os.sep, test)) # specs have .exe hardcoded

if __name__ == '__main__':
    if len(sys.argv) == 1:
        clean()
        runtests()
    if '--clean' in sys.argv:
        clean()
    if '--run' in sys.argv:
        runtests()
    raw_input("Press any key to exit")
