#! /usr/bin/env python

""" Make.py

    -h help
    -n use separate archive / executable (nonELF)
    -e use concatenated executable / archive (ELF)
    -p prefix
    -P execprefix
"""
import sys
import os
import getopt
import string
import marshal
import parsesetup
import bkfile
import makemakefile
import pprint

def main():
    dirnm = os.path.dirname(sys.argv[0])
    if dirnm not in ('', '.'):
        os.chdir(dirnm)
    # overridable context
    prefix = None                       # settable with -p option
    exec_prefix = None                  # settable with -P option
    non_elf = 1                         # settable with -e option
    if ( sys.platform[:5] == 'linux' or
         sys.platform[:3] == 'win' or
         sys.platform[:7] == 'freebsd' or
         sys.platform[:6] == 'cygwin' ):
        non_elf = 0                         # settable with -n option

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hneo:p:P:')
    except getopt.error, msg:
        usage('getopt error: ' + str(msg))

    # proces option arguments
    for o, a in opts:
        if o == '-h':
            print __doc__
            return
        if o == '-p':
            prefix = a
        if o == '-P':
            exec_prefix = a
        if o == '-n':
            non_elf = 1
        if o == '-e':
            non_elf = 0
    # default prefix and exec_prefix
    if not exec_prefix:
        if prefix:
            exec_prefix = prefix
        else:
            exec_prefix = sys.exec_prefix
    if not prefix:
        prefix = sys.prefix
    # determine whether -p points to the Python source tree
    ishome = os.path.exists(os.path.join(prefix, 'Python', 'ceval.c'))
    cygwin = sys.platform == 'cygwin'

    if ishome:
        print "(Using Python source directory)"
        binlib = exec_prefix
        incldir = os.path.join(prefix, 'Include')
        config_h_dir = exec_prefix
        makefile_in = os.path.join(exec_prefix, 'Modules', 'Makefile')
    else:
        if cygwin:
            binlib = os.path.join('/lib', 'python%s' % sys.version[:3], 'config')
        else:
            binlib = os.path.join(exec_prefix,
                              'lib', 'python%s' % sys.version[:3], 'config')
        incldir = os.path.join(prefix, 'include', 'python%s' % sys.version[:3])
        config_h_dir = os.path.join(exec_prefix, 'include',
                                    'python%s' % sys.version[:3])
        makefile_in = os.path.join(binlib, 'Makefile')

    # salt config.dat with the exe type
    try:
        config = eval(open('../../config.dat', 'r').read())
    except IOError:
        config = {}
    config['useELFEXE'] = not non_elf
    configf = open('../../config.dat', 'w')
    pprint.pprint(config, configf)
    configf.close()
    
    targets = [None, None]
    targets[0] = os.path.join('../../support', 'run')
    targets[1] = os.path.join('../../support', 'run_d')
    
    includes = ['-I../common', '-I' + incldir, '-I' + config_h_dir]

    have_warnings = 0
    import exceptions
    if not hasattr(exceptions, '__file__'):
        freeze_exceptions = 0
        files = ['main.c', '../common/launch.c']
        if hasattr(exceptions, 'Warning'):
            have_warnings = 1
    else:
        freeze_exceptions = 1
        import exceptions
        print "reading exceptions from", exceptions.__file__
        inf = open(exceptions.__file__, 'rb')
        inf.seek(8)
        code = inf.read()
        codelen = len(code)
        outfp = bkfile.open('M_exceptions.c', 'w')
        files = ['M_exceptions.c', 'main.c', '../common/launch.c']
        outfp.write('unsigned char M_exceptions[] = {')
        for i in range(0, len(code), 16):
            outfp.write('\n\t')
            for c in code[i:i+16]:
                outfp.write('%d,' % ord(c))
        outfp.write('\n};\n')
        outfp.close()

    cflags = includes + ['$(OPT)']
    if have_warnings:
        cflags.append('-DHAVE_WARNINGS')
    if freeze_exceptions:
        cflags.append('-DFREEZE_EXCEPTIONS')
        cflags.append('-DEXCEPTIONS_LEN=%d' % codelen)
    if non_elf:
        cflags.append('-DNONELF')
    if cygwin:
        libs = [os.path.join(binlib, 'libpython$(VERSION).dll.a')]
    else:
        libs = [os.path.join(binlib, 'libpython$(VERSION).a')]

    somevars = {}
    if os.path.exists(makefile_in):
        makevars = parsesetup.getmakevars(makefile_in)
    else:
        raise ValueError, "Makefile '%s' not found" % makefile_in
    for key in makevars.keys():
        somevars[key] = makevars[key]

    somevars['CFLAGS'] = string.join(cflags) # override
    files = ['$(OPT)', '$(LDFLAGS)', '$(LINKFORSHARED)', 'getpath.c'] + \
            files + libs + \
            ['$(MODLIBS)', '$(LIBS)', '$(SYSLIBS)', '-lz']  # XXX zlib not always -lz

    outfp = bkfile.open('Makefile', 'w')
    try:
        makemakefile.writevars(outfp, somevars, string.join(targets))
        makemakefile.writerules(outfp, files[:], '', '', targets[0])
        makemakefile.writerules(outfp, files[:], '_d', '-D_DEBUG -DLAUNCH_DEBUG', targets[1])
    finally:
        outfp.close()

    # Done!

    print 'Now run "make" to build the targets:', string.join(targets)


def usage(msg):
    sys.stdout = sys.stderr
    print "Error:", msg
    print "Use ``%s -h'' for help" % sys.argv[0]
    sys.exit(2)


main()
