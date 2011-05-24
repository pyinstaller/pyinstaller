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
import traceback

from PyInstaller import is_win, is_cygwin, is_darwin, is_py26

try:
    # zipfile is available since Python 1.6. Here it is only required for
    # extracting eggs, which are not supported prior to 2.3 anyway
    import zipfile
except ImportError:
    pass


seen = {}
_bpath = None

silent = False  # True suppresses all informative messages from the dependency code

if is_win:
    if is_py26:
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

    def get_windows_dir():
        """Return the Windows directory e.g. C:\\Windows"""
        try:
            import win32api
        except ImportError:
            windir = os.getenv('SystemRoot', os.getenv('WINDIR'))
        else:
            windir = win32api.GetWindowsDirectory()
        if not windir:
            print "E: Cannot determine your Windows directory"
            sys.exit(1)
        return windir

# regex excludes
excludes = {
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
    r'^Microsoft\.Windows\.Common-Controls$':1,
}

# regex includes - overrides excludes
includes = {}

# Darwin has a stable ABI for applications, so there is no need
# to include either /usr/lib nor system frameworks.
if is_darwin:
    excludes['^/usr/lib/'] = 1
    excludes['^/System/Library/Frameworks'] = 1

if is_win:
    sep = '[%s]' % re.escape(os.sep + os.altsep)
    # Exclude everything from the Windows directory by default
    excludes['^%s%s' % (re.escape(get_windows_dir()), sep)] = 1
    # Allow pythonNN.dll, pythoncomNN.dll, pywintypesNN.dll
    includes[r'%spy(?:thon(?:com)?|wintypes)\d+\.dll$' % sep] = 1

excludesRe = re.compile('|'.join(excludes.keys()), re.I)
includesRe = re.compile('|'.join(includes.keys()), re.I)

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


def _getImports_pe(pth):
    """Find the binary dependencies of PTH.

        This implementation walks through the PE header
        and uses library pefile for that and supports
        32/64bit Windows"""
    import PyInstaller.lib.pefile as pefile
    pe = pefile.PE(pth)
    dlls = []
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dlls.append(entry.dll)
    return dlls


def Dependencies(lTOC, xtrapath=None, manifest=None):
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
        if is_win:
            for ftocnm, fn in selectAssemblies(pth, manifest):
                lTOC.append((ftocnm, fn, 'BINARY'))
        for lib, npth in selectImports(pth, xtrapath):
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
        if (excludesRe.search(assembly.name) and (not includes or
            not includesRe.search(assembly.name))):
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

def selectImports(pth, xtrapath=None):
    """Return the dependencies of a binary that should be included.

    Return a list of pairs (name, fullpath)
    """
    rv = []
    if xtrapath is None:
        xtrapath = [os.path.dirname(pth)]
    else:
        assert isinstance(xtrapath, list)
        xtrapath = [os.path.dirname(pth)] + xtrapath # make a copy
    dlls = getImports(pth)
    for lib in dlls:
        if seen.get(string.upper(lib),0):
            continue
        if not is_win and not is_cygwin:
            # all other platforms
            npth = lib
            dir, lib = os.path.split(lib)
        else:
            # plain win case
            npth = getfullnameof(lib, xtrapath)

        # now npth is a candidate lib if found
        # check again for excludes but with regex FIXME: split the list
        if npth:
            candidatelib = npth
        else:
            candidatelib = lib
        if (excludesRe.search(candidatelib) and (not includes or
            not includesRe.search(candidatelib))):
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
    fwpaths = filter(None, os.environ.get('DYLD_FRAMEWORK_PATH', '').split(':'))
    fwpaths.extend(['/Library/Frameworks', '/Network/Library/Frameworks',
                    '/System/Library/Frameworks'])
    rslt = []
    for line in os.popen('otool -L "%s"' % pth).readlines():
        m = re.search(r"\s+(.*?)\s+\(.*\)", line)
        if m:
            lib = m.group(1)
            if lib.startswith("@executable_path"):
                rel_path = lib.replace("@executable_path", ".")
                rel_path = os.path.join(os.path.dirname(pth), rel_path)
                lib = os.path.abspath(rel_path)
            elif lib.startswith("@loader_path"):
                rel_path = lib.replace("@loader_path", ".")
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
                print 'E: cannot find path %s (needed by %s)' % (lib, pth)

    return rslt

def getImports(pth):
    """Forwards to the correct getImports implementation for the platform.
    """
    if not os.path.isfile(pth):
        pth = check_extract_from_egg(pth)[0][0]
    if is_win or is_cygwin:
        if pth.lower().endswith(".manifest"):
            return []
        try:
            return _getImports_pe(pth)
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
    elif is_darwin:
        return _getImports_otool(pth)
    else:
        return _getImports_ldd(pth)

def getWindowsPath():
    """Return the path that Windows will search for dlls."""
    global _bpath
    if _bpath is None:
        _bpath = []
        if is_win:
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
