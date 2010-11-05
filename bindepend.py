#! /usr/bin/env python
#
# Find external dependencies of binary libraries.
#
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

# use dumpbin.exe (if present) to find the binary
# dependencies of an extension module.
# if dumpbin not available, pick apart the PE hdr of the binary
# while this appears to work well, it is complex and subject to
# problems with changes to PE hdrs (ie, this works only on 32 bit Intel
# Windows format binaries)
#
# Note also that you should check the results to make sure that the
# dlls are redistributable. I've listed most of the common MS dlls
# under "excludes" below; add to this list as necessary (or use the
# "excludes" option in the INSTALL section of the config file).

import os
import time
import string
import sys
import re
from glob import glob

seen = {}
_bpath = None
iswin = sys.platform[:3] == 'win'
cygwin = sys.platform == 'cygwin'
darwin = sys.platform[:6] == 'darwin'

silent = False  # True suppresses all informative messages from the dependency code

if iswin:
    import shutil
    import traceback
    import zipfile

    if hasattr(sys, "version_info") and sys.version_info[:2] >= (2,6):
        try:
            import win32api
            import pywintypes
        except ImportError:
            print "ERROR: Python 2.6+ on Windows support needs pywin32"
            print "Please install http://sourceforge.net/projects/pywin32/"
            sys.exit(2)

    from winmanifest import RT_MANIFEST, GetManifestResources, Manifest
    try:
        from winmanifest import winresource
    except ImportError, detail:
        winresource = None

excludes = {
    'KERNEL32.DLL':1,
    'ADVAPI.DLL':1,
    'MSVCRT.DLL':1,
    'ADVAPI32.DLL':1,
    'COMCTL32.DLL':1,
    'CRTDLL.DLL':1,
    'GDI32.DLL':1,
    'MFC42.DLL':1,
    'NTDLL.DLL':1,
    'OLE32.DLL':1,
    'OLEAUT32.DLL':1,
    'RPCRT4.DLL':1,
    'SHELL32.DLL':1,
    'USER32.DLL':1,
    'WINSPOOL.DRV':1,
    'WS2HELP.DLL':1,
    'WS2_32.DLL':1,
    'WSOCK32.DLL':1,
    'MSWSOCK.DLL':1,
    'WINMM.DLL':1,
    'COMDLG32.DLL':1,
##    'ZLIB.DLL':1,   # test with python 1.5.2
    'ODBC32.DLL':1,
    'VERSION.DLL':1,
    'IMM32.DLL':1,
    'DDRAW.DLL':1,
    'DCIMAN32.DLL':1,
    'OPENGL32.DLL':1,
    'GLU32.DLL':1,
    'GLUB32.DLL':1,
    'NETAPI32.DLL':1,
    'MSCOREE.DLL':1,
    'PSAPI.DLL':1,
    'MSVCP80.DLL':1,
    'MSVCR80.DLL':1,
    'MSVCP90.DLL':1,
    'MSVCR90.DLL':1,
    'IERTUTIL.DLL':1,
    'POWRPROF.DLL':1,
    'SHLWAPI.DLL':1,
    'URLMON.DLL':1,
    'MSIMG32.DLL':1,
    'MPR.DLL':1,
    'DNSAPI.DLL':1,
    'RASAPI32.DLL':1,
    # regex excludes
    r'/libc\.so\..*':1,
    r'/libdl\.so\..*':1,
    r'/libm\.so\..*':1,
    r'/libpthread\.so\..*':1,
    r'/librt\.so\..*':1,
    r'/libthread_db\.so\..*':1,
    r'/libdb-.*\.so':1,
    # libGL can reference some hw specific libraries (like nvidia libs)
    r'/libGL\..*':1,
    # MS assembly excludes
    'Microsoft.Windows.Common-Controls':1,
}

# Darwin has a stable ABI for applications, so there is no need
# to include either /usr/lib nor system frameworks.
if darwin:
    excludes['^/usr/lib/'] = 1
    excludes['^/System/Library/Frameworks'] = 1

excludesRe = re.compile('|'.join(excludes.keys()), re.I)

def getfullnameof(mod, xtrapath = None):
    """Return the full path name of MOD.

        MOD is the basename of a dll or pyd.
        XTRAPATH is a path or list of paths to search first.
        Return the full path name of MOD.
        Will search the full Windows search path, as well as sys.path"""
    # Search sys.path first!
    epath = sys.path + getWindowsPath()
    if xtrapath is not None:
        if type(xtrapath) == type(''):
            epath.insert(0, xtrapath)
        else:
            epath = xtrapath + epath
    for p in epath:
        npth = os.path.join(p, mod)
        if os.path.exists(npth):
            return npth
        # second try: lower case filename
        for p in epath:
            npth = os.path.join(p, string.lower(mod))
            if os.path.exists(npth):
                return npth
    return ''

# TODO function is not used - remove?
def _getImports_dumpbin(pth):
    """Find the binary dependencies of PTH.

        This implementation (not used right now) uses the MSVC utility dumpbin"""
    import tempfile
    rslt = []
    tmpf = tempfile.mktemp()
    os.system('dumpbin /IMPORTS "%s" >%s' %(pth, tmpf))
    time.sleep(0.1)
    txt = open(tmpf,'r').readlines()
    os.remove(tmpf)
    i = 0
    while i < len(txt):
        tokens = string.split(txt[i])
        if len(tokens) == 1 and string.find(tokens[0], '.') > 0:
            rslt.append(string.strip(tokens[0]))
        i = i + 1
    return rslt

def _getImports_pe_lib_pefile(pth):
    """Find the binary dependencies of PTH.

        This implementation walks through the PE header
        and uses library pefile for that and supports
        32/64bit Windows"""
    import pefile
    pe = pefile.PE(pth)
    dlls = []
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dlls.append(entry.dll)
    return dlls


# TODO function is not used - remove?
def _getImports_pe_x(pth):
    """Find the binary dependencies of PTH.

        This implementation walks through the PE header"""
    import struct
    rslt = []
    try:
        f = open(pth, 'rb').read()
        pehdrd = struct.unpack('l', f[60:64])[0]  #after the MSDOS loader is the offset of the peheader
        magic = struct.unpack('l', f[pehdrd:pehdrd+4])[0] # pehdr starts with magic 'PE\000\000' (or 17744)
                                                          # then 20 bytes of COFF header
        numsecs = struct.unpack('h', f[pehdrd+6:pehdrd+8])[0] # whence we get number of sections
        opthdrmagic = struct.unpack('h', f[pehdrd+24:pehdrd+26])[0]
        if opthdrmagic == 0x10b: # PE32 format
            numdictoffset = 116
            importoffset = 128
        elif opthdrmagic == 0x20b: # PE32+ format
            numdictoffset = 132
            importoffset = 148
        else:
            print "E: bindepend cannot analyze %s - unknown header format! %x" % (pth, opthdrmagic)
            return rslt
        numdirs = struct.unpack('l', f[pehdrd+numdictoffset:pehdrd+numdictoffset+4])[0]
        idata = ''
        if magic == 17744:
            importsec, sz = struct.unpack('2l', f[pehdrd+importoffset:pehdrd+importoffset+8])
            if sz == 0:
                return rslt
            secttbl = pehdrd + numdictoffset + 4 + 8*numdirs
            secttblfmt = '8s7l2h'
            seclist = []
            for i in range(numsecs):
                seclist.append(struct.unpack(secttblfmt, f[secttbl+i*40:secttbl+(i+1)*40]))
                #nm, vsz, va, rsz, praw, preloc, plnnums, qrelocs, qlnnums, flags \
                # = seclist[-1]
            for i in range(len(seclist)-1):
                if seclist[i][2] <= importsec < seclist[i+1][2]:
                    break
            vbase = seclist[i][2]
            raw = seclist[i][4]
            idatastart = raw + importsec - vbase
            idata = f[idatastart:idatastart+seclist[i][1]]
            i = 0
            while 1:
                chunk = idata[i*20:(i+1)*20]
                if len(chunk) != 20:
                    print "E: premature end of import table (chunk is %d, not 20)" % len(chunk)
                    break
                vsa =  struct.unpack('5l', chunk)[3]
                if vsa == 0:
                    break
                sa = raw + vsa - vbase
                end = string.find(f, '\000', sa)
                nm = f[sa:end]
                if nm:
                    rslt.append(nm)
                i = i + 1
        else:
            print "E: bindepend cannot analyze %s - file is not in PE format!" % pth
    except IOError:
        print "E: bindepend cannot analyze %s - file not found!" % pth
    #except struct.error:
    #    print "E: bindepend cannot analyze %s - error walking thru pehdr" % pth
    return rslt

def _getImports_pe(path):
    """Find the binary dependencies of PTH.

        This implementation walks through the PE header"""
    import struct
    f = open(path, 'rb')
    # skip the MSDOS loader
    f.seek(60)
    # get offset to PE header
    offset = struct.unpack('l', f.read(4))[0]
    f.seek(offset)
    signature = struct.unpack('l', f.read(4))[0]
    coffhdrfmt = 'hhlllhh'
    rawcoffhdr = f.read(struct.calcsize(coffhdrfmt))
    coffhdr = struct.unpack(coffhdrfmt, rawcoffhdr)
    coffhdr_numsections = coffhdr[1]

    opthdrfmt = 'hbblllllllllhhhhhhllllhhllllll'
    rawopthdr = f.read(struct.calcsize(opthdrfmt))
    opthdr = struct.unpack(opthdrfmt, rawopthdr)
    opthdr_numrvas = opthdr[-1]

    datadirs = []
    datadirsize = struct.calcsize('ll') # virtual address, size
    for i in range(opthdr_numrvas):
        rawdatadir = f.read(datadirsize)
        datadirs.append(struct.unpack('ll', rawdatadir))

    sectionfmt = '8s6l2hl'
    sectionsize = struct.calcsize(sectionfmt)
    sections = []
    for i in range(coffhdr_numsections):
        rawsection = f.read(sectionsize)
        sections.append(struct.unpack(sectionfmt, rawsection))

    importva, importsz = datadirs[1]
    if importsz == 0:
        return []
    # figure out what section it's in
    NAME, MISC, VIRTADDRESS, RAWSIZE, POINTERTORAW = range(5)
    for j in range(len(sections)-1):
        if sections[j][VIRTADDRESS] <= importva < sections[j+1][VIRTADDRESS]:
            importsection = sections[j]
            break
    else:
        if importva >= sections[-1][VIRTADDRESS]:
            importsection = sections[-1]
        else:
            print "E: import section is unavailable"
            return []
    f.seek(importsection[POINTERTORAW] + importva - importsection[VIRTADDRESS])
    data = f.read(importsz)
    iidescrfmt = 'lllll'
    CHARACTERISTICS, DATETIME, FWDRCHAIN, NAMERVA, FIRSTTHUNK = range(5)
    iidescrsz = struct.calcsize(iidescrfmt)
    dlls = []
    while data:
        iid = struct.unpack(iidescrfmt, data[:iidescrsz])
        if iid[NAMERVA] == 0:
            break
        f.seek(importsection[POINTERTORAW] + iid[NAMERVA] - importsection[VIRTADDRESS])
        nm = f.read(256)
        nm, jnk = string.split(nm, '\0', 1)
        if nm:
            dlls.append(nm)
        data = data[iidescrsz:]
    return dlls

def Dependencies(lTOC, platform=sys.platform, xtrapath=None, manifest=None):
    """Expand LTOC to include all the closure of binary dependencies.

       LTOC is a logical table of contents, ie, a seq of tuples (name, path).
       Return LTOC expanded by all the binary dependencies of the entries
       in LTOC, except those listed in the module global EXCLUDES

       manifest should be a winmanifest.Manifest instance on Windows, so
       that all dependent assemblies can be added"""
    for nm, pth, typ in lTOC:
        if seen.get(string.upper(nm),0):
            continue
        if not silent:
            print "I: Analyzing", pth
        seen[string.upper(nm)] = 1
        if iswin:
            for ftocnm, fn in selectAssemblies(pth, manifest):
                lTOC.append((ftocnm, fn, 'BINARY'))
        for lib, npth in selectImports(pth, platform, xtrapath):
            if seen.get(string.upper(lib),0) or seen.get(string.upper(npth),0):
                continue
            seen[string.upper(npth)] = 1
            lTOC.append((lib, npth, 'BINARY'))

    return lTOC

def pkg_resouces_get_default_cache():
    """Determine the default cache location

    This returns the ``PYTHON_EGG_CACHE`` environment variable, if set.
    Otherwise, on Windows, it returns a "Python-Eggs" subdirectory of the
    "Application Data" directory.  On all other systems, it's "~/.python-eggs".
    """
    # This function borrowed from setuptools/pkg_resources
    try:
        return os.environ['PYTHON_EGG_CACHE']
    except KeyError:
        pass

    if os.name!='nt':
        return os.path.expanduser('~/.python-eggs')

    app_data = 'Application Data'   # XXX this may be locale-specific!
    app_homes = [
        (('APPDATA',), None),       # best option, should be locale-safe
        (('USERPROFILE',), app_data),
        (('HOMEDRIVE','HOMEPATH'), app_data),
        (('HOMEPATH',), app_data),
        (('HOME',), None),
        (('WINDIR',), app_data),    # 95/98/ME
    ]

    for keys, subdir in app_homes:
        dirname = ''
        for key in keys:
            if key in os.environ:
                dirname = os.path.join(dirname, os.environ[key])
            else:
                break
        else:
            if subdir:
                dirname = os.path.join(dirname,subdir)
            return os.path.join(dirname, 'Python-Eggs')
    else:
        raise RuntimeError(
            "Please set the PYTHON_EGG_CACHE enviroment variable"
        )

def check_extract_from_egg(pth, todir=None):
    r"""Check if path points to a file inside a python egg file, extract the
       file from the egg to a cache directory (following pkg_resources
       convention) and return [(extracted path, egg file path, relative path
       inside egg file)].
       Otherwise, just return [(original path, None, None)].
       If path points to an egg file directly, return a list with all files
       from the egg formatted like above.

       Example:
       >>> check_extract_from_egg(r'C:\Python26\Lib\site-packages\my.egg\mymodule\my.pyd')
       [(r'C:\Users\UserName\AppData\Roaming\Python-Eggs\my.egg-tmp\mymodule\my.pyd',
         r'C:\Python26\Lib\site-packages\my.egg', r'mymodule/my.pyd')]
       """
    rv = []
    if os.path.altsep:
        pth = pth.replace(os.path.altsep, os.path.sep)
    components = pth.split(os.path.sep)
    for i, name in enumerate(components):
        if name.lower().endswith(".egg"):
            eggpth = os.path.sep.join(components[:i + 1])
            if os.path.isfile(eggpth):
                # eggs can also be directories!
                try:
                    egg = zipfile.ZipFile(eggpth)
                except zipfile.BadZipfile, e:
                    print "E:", eggpth, e
                    sys.exit(1)
                if todir is None:
                    # Use the same directory as setuptools/pkg_resources. So,
                    # if the specific egg was accessed before (not necessarily
                    # by pyinstaller), the extracted contents already exist
                    # (pkg_resources puts them there) and can be used.
                    todir = os.path.join(pkg_resouces_get_default_cache(),
                                         name + "-tmp")
                if components[i + 1:]:
                    members = ["/".join(components[i + 1:])]
                else:
                    members = egg.namelist()
                for member in members:
                    pth = os.path.join(todir, member)
                    if not os.path.isfile(pth):
                        dirname = os.path.dirname(pth)
                        if not os.path.isdir(dirname):
                            os.makedirs(dirname)
                        f = open(pth, "wb")
                        f.write(egg.read(member))
                        f.close()
                    rv.append((pth, eggpth, member))
                return rv
    return [(pth, None, None)]

def getAssemblies(pth):
    """Return the dependent assemblies of a binary."""
    if not os.path.isfile(pth):
        pth = check_extract_from_egg(pth)[0][0]
    if pth.lower().endswith(".manifest"):
        return []
    # check for manifest file
    manifestnm = pth + ".manifest"
    if os.path.isfile(manifestnm):
        fd = open(manifestnm, "rb")
        res = {RT_MANIFEST: {1: {0: fd.read()}}}
        fd.close()
    elif not winresource:
        # resource access unavailable (needs pywin32)
        return []
    else:
        # check the binary for embedded manifest
        try:
            res = GetManifestResources(pth)
        except winresource.pywintypes.error, exc:
            if exc.args[0] == winresource.ERROR_BAD_EXE_FORMAT:
                if not silent:
                    print 'I: Cannot get manifest resource from non-PE file:'
                    print 'I:', pth
                return []
            raise
    rv = []
    if RT_MANIFEST in res and len(res[RT_MANIFEST]):
        for name in res[RT_MANIFEST]:
            for language in res[RT_MANIFEST][name]:
                # check the manifest for dependent assemblies
                try:
                    manifest = Manifest()
                    manifest.filename = ":".join([pth, str(RT_MANIFEST),
                                                  str(name), str(language)])
                    manifest.parse_string(res[RT_MANIFEST][name][language],
                                          False)
                except Exception, exc:
                    print ("E: Cannot parse manifest resource %s, %s "
                           "from") % (name, language)
                    print "E:", pth
                    print "E:",
                    traceback.print_exc()
                else:
                    if manifest.dependentAssemblies and not silent:
                        print "I: Dependent assemblies of %s:" % pth
                        print "I:", ", ".join([assembly.getid()
                                               for assembly in
                                               manifest.dependentAssemblies])
                    rv.extend(manifest.dependentAssemblies)
    return rv

def selectAssemblies(pth, manifest=None):
    """Return a binary's dependent assemblies files that should be included.

    Return a list of pairs (name, fullpath)
    """
    rv = []
    if not os.path.isfile(pth):
        pth = check_extract_from_egg(pth)[0][0]
    for assembly in getAssemblies(pth):
        if seen.get(assembly.getid().upper(),0):
            continue
        if manifest:
            # Add assembly as dependency to our final output exe's manifest
            if not assembly.name in [dependentAssembly.name
                                     for dependentAssembly in
                                     manifest.dependentAssemblies]:
                print ("Adding %s to dependent assemblies "
                       "of final executable") % assembly.name
                manifest.dependentAssemblies.append(assembly)
        if excludesRe.search(assembly.name):
            if not silent:
                print "I: Skipping assembly", assembly.getid()
            continue
        if assembly.optional:
            if not silent:
                print "I: Skipping optional assembly", assembly.getid()
            continue
        files = assembly.find_files()
        if files:
            seen[assembly.getid().upper()] = 1
            for fn in files:
                fname, fext = os.path.splitext(fn)
                if fext.lower() == ".manifest":
                    nm = assembly.name + fext
                else:
                    nm = os.path.basename(fn)
                ftocnm = nm
                if assembly.language not in (None, "", "*", "neutral"):
                    ftocnm = os.path.join(assembly.getlanguage(),
                                          ftocnm)
                nm, ftocnm, fn = [item.encode(sys.getfilesystemencoding())
                                  for item in
                                  (nm,
                                   ftocnm,
                                   fn)]
                if not seen.get(fn.upper(),0):
                    if not silent:
                        print "I: Adding", ftocnm
                    seen[nm.upper()] = 1
                    seen[fn.upper()] = 1
                    rv.append((ftocnm, fn))
                else:
                    #print "I: skipping", ftocnm, "part of assembly", \
                    #      assembly.name, "dependency of", pth
                    pass
        else:
            print "E: Assembly", assembly.getid(), "not found"
    return rv

def selectImports(pth, platform=sys.platform, xtrapath=None):
    """Return the dependencies of a binary that should be included.

    Return a list of pairs (name, fullpath)
    """
    rv = []
    if xtrapath is None:
        xtrapath = [os.path.dirname(pth)]
    else:
        assert isinstance(xtrapath, list)
        xtrapath = [os.path.dirname(pth)] + xtrapath # make a copy
    dlls = getImports(pth, platform=platform)
    for lib in dlls:
        if seen.get(string.upper(lib),0):
            continue
        if not iswin and not cygwin:
            # all other platforms
            npth = lib
            dir, lib = os.path.split(lib)
            if excludes.get(dir,0):
                continue
        else:
            # plain win case
            npth = getfullnameof(lib, xtrapath)

        # now npth is a candidate lib if found
        # check again for excludes but with regex FIXME: split the list
        if npth:
            candidatelib = npth
        else:
            candidatelib = lib
        if excludesRe.search(candidatelib):
            if candidatelib.find('libpython') < 0 and \
               candidatelib.find('Python.framework') < 0:
                # skip libs not containing (libpython or Python.framework)
                if not silent and \
                   not seen.get(string.upper(npth),0):
                    print "I: Skipping", lib, "dependency of", \
                          os.path.basename(pth)
                continue
            else:
                pass

        if npth:
            if not seen.get(string.upper(npth),0):
                if not silent:
                    print "I: Adding", lib, "dependency of", \
                          os.path.basename(pth)
                rv.append((lib, npth))
        else:
            print "E: lib not found:", lib, "dependency of", pth

    return rv

def _getImports_ldd(pth):
    """Find the binary dependencies of PTH.

        This implementation is for ldd platforms"""
    rslt = []
    for line in os.popen('ldd "%s"' % pth).readlines():
        m = re.search(r"\s+(.*?)\s+=>\s+(.*?)\s+\(.*\)", line)
        if m:
            name, lib = m.group(1), m.group(2)
            if name[:10] in ('linux-gate', 'linux-vdso'):
                # linux-gate is a fake library which does not exist and
                # should be ignored. See also:
                # http://www.trilithium.com/johan/2005/08/linux-gate/
                continue
            if os.path.exists(lib):
                rslt.append(lib)
            else:
                print 'E: cannot find %s in path %s (needed by %s)' % \
                      (name, lib, pth)
    return rslt

def _getImports_otool(pth):
    """Find the binary dependencies of PTH.

        This implementation is for otool platforms"""
    # dyld searches these paths for framework libs
    # we ignore DYLD_FALLBACK_LIBRARY_PATH for now (man dyld)
    fwpaths = ['/Library/Frameworks', '/Network/Library/Frameworks', '/System/Library/Frameworks']
    for p in reversed(os.environ.get('DYLD_FRAMEWORK_PATH', '').split(':')):
        if p:
            fwpaths.insert(0, p)
    rslt = []
    for line in os.popen('otool -L "%s"' % pth).readlines():
        m = re.search(r"\s+(.*?)\s+\(.*\)", line)
        if m:
            lib = m.group(1)
            if lib.startswith("@executable_path"):
                rel_path = lib.replace("@executable_path",".")
                rel_path = os.path.join(os.path.dirname(pth), rel_path)
                lib = os.path.abspath(rel_path)
            elif lib.startswith("@loader_path"):
                rel_path = lib.replace("@loader_path",".")
                rel_path = os.path.join(os.path.dirname(pth), rel_path)
                lib = os.path.abspath(rel_path)
            elif not os.path.isabs(lib):
                # lookup matching framework path, if relative pathname
                for p in fwpaths:
                    fwlib = os.path.join(p, lib)
                    if os.path.exists(fwlib):
                        lib = fwlib
                        break
            if os.path.exists(lib):
                rslt.append(lib)
            else:
                print 'E: cannot find path %s (needed by %s)' % \
                      (lib, pth)

    return rslt

def getImports(pth, platform=sys.platform):
    """Forwards to the correct getImports implementation for the platform.
    """
    if not os.path.isfile(pth):
        pth = check_extract_from_egg(pth)[0][0]
    if platform[:3] == 'win' or platform == 'cygwin':
        if pth.lower().endswith(".manifest"):
            return []
        try:
            return _getImports_pe_lib_pefile(pth)
        except Exception, exception:
            # Assemblies can pull in files which aren't necessarily PE,
            # but are still needed by the assembly. Any additional binary
            # dependencies should already have been handled by
            # selectAssemblies in that case, so just warn, return an empty
            # list and continue.
            if not silent:
                print 'W: Cannot get binary dependencies for file:'
                print 'W:', pth
                print 'W:',
                traceback.print_exc()
            return []
    elif platform == 'darwin':
        return _getImports_otool(pth)
    else:
        return _getImports_ldd(pth)

def getWindowsPath():
    """Return the path that Windows will search for dlls."""
    global _bpath
    if _bpath is None:
        _bpath = []
        if iswin:
            try:
                import win32api
            except ImportError:
                print "W: Cannot determine your Windows or System directories"
                print "W: Please add them to your PATH if .dlls are not found"
                print "W: or install http://sourceforge.net/projects/pywin32/"
            else:
                sysdir = win32api.GetSystemDirectory()
                sysdir2 = os.path.normpath(os.path.join(sysdir, '..', 'SYSTEM'))
                windir = win32api.GetWindowsDirectory()
                _bpath = [sysdir, sysdir2, windir]
        _bpath.extend(string.split(os.environ.get('PATH', ''), os.pathsep))
    return _bpath

def findLibrary(name):
    """Look for a library in the system.

    Emulate the algorithm used by dlopen.

    `name`must include the prefix, e.g. ``libpython2.4.so``
    """
    assert sys.platform == 'linux2', "Current implementation for Linux only"

    lib = None

    # Look in the LD_LIBRARY_PATH
    lp = os.environ.get('LD_LIBRARY_PATH')
    if lp:
        for path in string.split(lp, os.pathsep):
            libs = glob(os.path.join(path, name + '*'))
            if libs:
                lib = libs[0]
                break

    # Look in /etc/ld.so.cache
    if lib is None:
        expr = r'/[^\(\)\s]*%s\.[^\(\)\s]*' % re.escape(name)
        m = re.search(expr, os.popen('/sbin/ldconfig -p 2>/dev/null').read())
        if m:
            lib = m.group(0)

    # Look in the known safe paths
    if lib is None:
        for path in ['/lib', '/usr/lib']:
            libs = glob(os.path.join(path, name + '*'))
            if libs:
                lib = libs[0]
                break

    # give up :(
    if lib is None:
        return None

    # Resolve the file name into the soname
    dir, file = os.path.split(lib)
    return os.path.join(dir, getSoname(lib))

def getSoname(filename):
    """Return the soname of a library."""
    cmd = "objdump -p -j .dynamic 2>/dev/null " + filename
    m = re.search(r'\s+SONAME\s+([^\s]+)', os.popen(cmd).read())
    if m: return m.group(1)


if __name__ == "__main__":
    from pyi_optparse import OptionParser
    parser = OptionParser(usage="%prog [options] <executable_or_dynamic_library>")
    parser.add_option('--target-platform', default=sys.platform,
                      help='Target platform, required for cross-bundling (default: current platform)')

    opts, args = parser.parse_args()
    silent = True  # Suppress all informative messages from the dependency code
    import glob
    for a in args:
        for fn in glob.glob(a):
            imports = getImports(fn, opts.target_platform)
            if opts.target_platform == "win32":
                imports.extend([a.getid() for a in getAssemblies(fn)])
            print fn, imports
