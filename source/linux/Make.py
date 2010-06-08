#! /usr/bin/env python
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

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
import bkfile
import makemakefile
import pprint

try:
    from distutils import sysconfig
except:
    print "ERROR: distutils with sysconfig required"
    sys.exit(1)

try:
    True
except NameError:
    True, False = 1, 0

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
         sys.platform[:7] in ['freebsd','darwin'] or
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
            exec_prefix = sysconfig.EXEC_PREFIX
    if not prefix:
        prefix = sysconfig.PREFIX

    # determine whether -p points to the Python source tree
    ishome = os.path.exists(os.path.join(prefix, 'Python', 'ceval.c'))

    cygwin = sys.platform == 'cygwin'
    darwin = sys.platform[:7] == 'darwin'

    if ishome:
        print "(Using Python source directory)"
        binlib = exec_prefix
        incldir = os.path.join(prefix, 'Include')
        includes = ['-I' + incldir]
        makefile_in = os.path.join(exec_prefix, 'Makefile')
    else:
#       binlib = os.path.join (sysconfig.get_python_lib(True, True, exec_prefix), 'config')
        binlib = sysconfig.get_config_vars('LIBDIR')[0]
        # TODO: Is it possible to have more than one path returned? if so fix "includes" list
        incldir_list =  sysconfig.get_config_vars('INCLUDEDIR')
        includes = []
        for dir in incldir_list:
            if dir != None:
                includes.append('-I' + dir)
        config_h_dir =  os.path.join (sysconfig.get_python_inc(True,exec_prefix))
        includes.append('-I' + config_h_dir)
        makefile_in = sysconfig.get_makefile_filename()

    # salt config.dat with the exe type
    try:
        config = eval(open('../../config.dat', 'r').read())
    except IOError:
        config = {}
    config['useELFEXE'] = not non_elf
    configf = open('../../config.dat', 'w')
    pprint.pprint(config, configf)
    configf.close()

    targets = [None, None, None, None]
    targets[0] = os.path.join('../../support/loader/', 'run')
    targets[1] = os.path.join('../../support/loader/', 'run_d')
    targets[2] = os.path.join('../../support/loader/', 'runw')
    targets[3] = os.path.join('../../support/loader/', 'runw_d')

    # include local 'common' dir
    includes.append('-I../common')

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

    includes.append('$(OPT)')
    cflags = includes
    cflags.append(sysconfig.get_config_vars('CFLAGS')[0]) #save sysconfig CFLAGS

    if have_warnings:
        cflags.append('-DHAVE_WARNINGS')
    if freeze_exceptions:
        cflags.append('-DFREEZE_EXCEPTIONS')
        cflags.append('-DEXCEPTIONS_LEN=%d' % codelen)
    if non_elf:
        cflags.append('-DNONELF')

#    libs = [os.path.join(sysconfig.get_config_vars('LIBDIR')[0], sysconfig.get_config_vars('INSTSONAME')[0])]

    somevars = {}
    if os.path.exists(makefile_in):
        print "Using '%s' as Makefile template" % makefile_in
        makevars = sysconfig.parse_makefile(makefile_in)
    else:
        raise ValueError, "Makefile '%s' not found" % makefile_in
    for key in makevars.keys():
        somevars[key] = makevars[key]

    somevars['CFLAGS'] = string.join(cflags) # override
    if sys.platform.startswith("darwin"):
        somevars['LDFLAGS'] += " -F$(PYTHONFRAMEWORKPREFIX)"
        somevars['LDFLAGS'] += " -mmacosx-version-min=%s" % somevars["MACOSX_DEPLOYMENT_TARGET"]
        somevars['LINKFORSHARED'] = "" #override
    files = ['$(OPT)', '$(LDFLAGS)', '$(LINKFORSHARED)', 'getpath.c'] + \
            files + \
            ['$(MODLIBS)', '$(LIBS)', '$(SYSLIBS)', '-lz']  # XXX zlib not always -lz


    ## Windowed and debug need per-target cflags and ldflags, we'll pass them to
    # makemakefile.writerules.
    flagsw = '-DWINDOWED'
    flags_d = '-D_DEBUG -DLAUNCH_DEBUG'
    ldflagsw = ''
    ldflags_d = ''

    if sys.platform.startswith("darwin"):
        flagsw += " -I/Developer/Headers/FlatCarbon"
        ldflagsw += " -framework Carbon"

    flagsw_d = ' '.join([flagsw, flags_d])
    ldflagsw_d = ' '.join([ldflagsw, ldflags_d])
    ##

    outfp = bkfile.open('Makefile', 'w')
    try:
        makemakefile.writevars(outfp, somevars, string.join(targets))
        makemakefile.writerules(outfp, files[:], '', '', '', targets[0])
        makemakefile.writerules(outfp, files[:], '_d', flags_d, ldflags_d, targets[1])
        makemakefile.writerules(outfp, files[:], 'w', flagsw, ldflagsw, targets[2])
        makemakefile.writerules(outfp, files[:], 'w_d', flagsw_d, ldflagsw_d, targets[3])
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
