#! /usr/bin/env python

import os, sys, string, shutil
HOME = os.path.dirname(sys.argv[0])
iswin = sys.platform[:3] == 'win'
cygwin = sys.platform == 'cygwin'
configfile = os.path.join(HOME, 'config.dat')
try:
    config = eval(open(configfile, 'r').read())
except IOError:
    config = {'useELFEXE':1}    # if not set by Make.py we can assume Windows

import mf, bindepend

# EXE_dependencies
print "I: computing EXE_dependencies"
python = sys.executable
if not iswin:
    while os.path.islink(python):
        python = os.readlink(python)
        if not os.path.isabs(python):
            for dir in string.split(os.environ['PATH'], os.pathsep):
                test = os.path.join(dir, python)
                if os.path.exists(test):
                    python = test
                    break
toc = bindepend.Dependencies([('', python, '')])
if iswin and sys.version[:3] == '1.5':
    import exceptions
    toc.append((os.path.basename(exceptions.__file__), exceptions.__file__, 'BINARY'))
config['EXE_dependencies'] = toc[1:]

_useTK = """\
import os, sys
try:
    basedir = os.environ['_MEIPASS2']
except KeyError:
    basedir = sys.path[0]
tcldir = os.path.join(basedir, '_MEI', 'tcl%s')
tkdir = os.path.join(basedir, '_MEI', 'tk%s')
os.environ["TCL_LIBRARY"] = tcldir
os.environ["TK_LIBRARY"] = tkdir
os.putenv("TCL_LIBRARY", tcldir)
os.putenv("TK_LIBRARY", tkdir)
"""

# TCL_root, TK_root and support/useTK.py
print "I: Finding TCL/TK..."
if not iswin:
    saveexcludes = bindepend.excludes
    bindepend.excludes = {}
import re
pattern = [r'libtcl(\d\.\d)?\.so', r'(?i)tcl(\d\d)\.dll'][iswin]
a = mf.ImportTracker()
a.analyze_r('Tkinter')
binaries = []
for modnm, mod in a.modules.items():
    if isinstance(mod, mf.ExtensionModule):
        binaries.append((mod.__name__, mod.__file__, 'EXTENSION'))
binaries.extend(bindepend.Dependencies(binaries))
binaries.extend(bindepend.Dependencies([('', sys.executable, '')]))
for nm, fnm, typ in binaries:
    mo = re.match(pattern, nm)
    if mo:
        ver = mo.group(1)
        tclbindir = os.path.dirname(fnm)
        if iswin:
            ver = ver[0] + '.' + ver[1:]
        elif ver is None:
            # we found "libtcl.so.0" so we need to get the version from the lib directory
            for name in os.listdir(tclbindir):
                mo = re.match(r'tcl(\d.\d)', name)
                if mo:
                    ver = mo.group(1)
        print "I: found TCL/TK version %s" % ver
        open(os.path.join(HOME, 'support/useTK.py'), 'w').write(_useTK % (ver, ver))
        tclnm = 'tcl%s' % ver
        tknm = 'tk%s' % ver
        # Linux: /usr/lib with the .tcl files in /usr/lib/tcl8.3 and /usr/lib/tk8.3
        # Windows: Python21/DLLs with the .tcl files in Python21/tcl/tcl8.3 and Python21/tcl/tk8.3
        #      or  D:/Programs/Tcl/bin with the .tcl files in D:/Programs/Tcl/lib/tcl8.0 and D:/Programs/Tcl/lib/tk8.0
        if iswin:
            for attempt in ['../tcl', '../lib']:
                if os.path.exists(os.path.join(tclbindir, attempt, tclnm)):
                    config['TCL_root'] = os.path.join(tclbindir, attempt, tclnm)
                    config['TK_root'] = os.path.join(tclbindir, attempt, tknm)
                    break
        else:
            config['TCL_root'] = os.path.join(tclbindir, tclnm)
            config['TK_root'] = os.path.join(tclbindir, tknm)
        break
else:
    print "I: could not find TCL/TK"
if not iswin:
    bindepend.excludes = saveexcludes

#useZLIB
print "I: testing for Zlib..."
try:
    import zlib
except ImportError:
    config['useZLIB'] = 0
    print 'I: ... Zlib unavailable'
else:
    config['useZLIB'] = 1
    print 'I: ... Zlib available'

#hasRsrcUpdate
if iswin:
    # only available on windows
    print "I: Testing for ability to set icons, version resources..."
    try:
        import win32api, icon, versionInfo
    except ImportError, detail:
        config['hasRsrcUpdate'] = 0
        print 'I: ... resource update unavailable -', detail
    else:
        test_exe = os.path.join(HOME, r'support\run.exe')
        if not os.path.exists( test_exe ):
            config['hasRsrcUpdate'] = 0
            print 'E: ... resource update unavailable - %s not found' % test_exe
        else:
            # The test_exe may be read-only
            # make a writable copy and test using that
            rw_test_exe = os.path.join( os.environ['TEMP'], 'me_test_exe.tmp' )
            shutil.copyfile( test_exe, rw_test_exe )
            try:
                hexe = win32api.BeginUpdateResource(rw_test_exe,0)
            except:
                config['hasRsrcUpdate'] = 0
                print 'I: ... resource update unavailable - win32api.BeginUpdateResource failed'
            else:
                win32api.EndUpdateResource(hexe, 1)
                config['hasRsrcUpdate'] = 1
                print 'I: ... resource update available'
            os.remove(rw_test_exe)
else:
    config['hasRsrcUpdate'] = 0

#hasUnicode
print 'I: Testing for Unicode support...'
try:
    import codecs
    config['hasUnicode'] = 1
    print 'I: ... Unicode available'
except ImportError:
    config['hasUnicode'] = 0
    print 'I: ... Unicode unavailable'

#hasUPX
print 'I: testing for UPX...'
hasUPX = 0
try:
    if iswin:
        os.system('upx -V >upx.txt')
        txt = open('upx.txt','r').read()
        os.remove('upx.txt')
        if txt[:3] == 'upx':
            hasUPX = 1
    else:
        rc = os.system('upx -V >/dev/null')
        hasUPX = ( rc == 0 )
    print 'I: ...UPX %s' % (('unavailable','available')[hasUPX])
except Exception, e:
    print 'I: ...exception result in testing for UPX'
    print e, e.args
config['hasUPX'] = hasUPX
        
# now write out config, so Build can load
outf = open(configfile, 'w')
import pprint
pprint.pprint(config, outf)
outf.close()

import Build

# PYZ_dependencies
print "I: computing PYZ dependencies..."
a = mf.ImportTracker([os.path.join(HOME, 'support')])
a.analyze_r('archive')
mod = a.modules['archive']
toc = Build.TOC([(mod.__name__, mod.__file__, 'PYMODULE')])
for i in range(len(toc)):
    nm, fnm, typ = toc[i]
    mod = a.modules[nm]
    tmp = []
    for importednm, isdelayed, isconditional in mod.imports:
        if not isconditional:
            realnms = a.analyze_one(importednm, nm)
            for realnm in realnms:
                imported = a.modules[realnm]
                if not isinstance(imported, mf.BuiltinModule):
                    tmp.append((imported.__name__, imported.__file__, imported.typ))
    toc.extend(tmp)
toc.reverse()
config['PYZ_dependencies'] = toc.data

outf = open(configfile, 'w')
import pprint
pprint.pprint(config, outf)
outf.close()

