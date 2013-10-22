#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Find external dependencies of binary libraries.
"""


import os
import sys
import re
from glob import glob

# Required for extracting eggs.
import zipfile


from PyInstaller.compat import is_win, is_unix, is_aix, is_cygwin, is_darwin, is_py26, is_py27, is_freebsd
from PyInstaller.depend import dylib
from PyInstaller.utils import winutils
import PyInstaller.compat as compat


import PyInstaller.log as logging
logger = logging.getLogger(__file__)

seen = {}

if is_win:
    if is_py26:
        try:
            # For Portable Python it is required to import pywintypes before
            # win32api module. See for details:
            # http://www.voidspace.org.uk/python/movpy/reference/win32ext.html#problems-with-win32api
            import pywintypes
            import win32api
        except ImportError:
            raise SystemExit("Error: PyInstaller for Python 2.6+ on Windows "
                 "needs pywin32.\r\nPlease install from "
                 "http://sourceforge.net/projects/pywin32/")

    from PyInstaller.utils.winmanifest import RT_MANIFEST
    from PyInstaller.utils.winmanifest import GetManifestResources
    from PyInstaller.utils.winmanifest import Manifest

    try:
        from PyInstaller.utils.winmanifest import winresource
    except ImportError, detail:
        winresource = None


def getfullnameof(mod, xtrapath=None):
    """
    Return the full path name of MOD.

    MOD is the basename of a dll or pyd.
    XTRAPATH is a path or list of paths to search first.
    Return the full path name of MOD.
    Will search the full Windows search path, as well as sys.path
    """
    # TODO: Allow in import-hooks to specify additional paths where the PyInstaller
    #       should look for other libraries.
    # SciPy/Numpy Windows builds from http://www.lfd.uci.edu/~gohlke/pythonlibs
    # Contain some dlls in directory like C:\Python27\Lib\site-packages\numpy\core\
    from distutils.sysconfig import get_python_lib
    numpy_core_paths = [os.path.join(get_python_lib(), 'numpy', 'core')]
    # In virtualenv numpy might be installed directly in real prefix path.
    # Then include this path too.
    if hasattr(sys, 'real_prefix'):
        numpy_core_paths.append(
            os.path.join(sys.real_prefix, 'Lib', 'site-packages', 'numpy', 'core')
        )

    # Search sys.path first!
    epath = sys.path + numpy_core_paths + winutils.get_system_path()
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
            npth = os.path.join(p, mod.lower())
            if os.path.exists(npth):
                return npth
    return ''


def _getImports_pe(pth):
    """
    Find the binary dependencies of PTH.

    This implementation walks through the PE header
    and uses library pefile for that and supports
    32/64bit Windows
    """
    import PyInstaller.lib.pefile as pefile
    dlls = set()
    # By default library pefile parses all PE information.
    # We are only interested in the list of dependent dlls.
    # Performance is improved by reading only needed information.
    # https://code.google.com/p/pefile/wiki/UsageExamples
    pe = pefile.PE(pth, fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    # Some libraries have no other binary dependencies. Use empty list
    # in that case. Otherwise pefile would return None.
    # e.g. C:\windows\system32\kernel32.dll on Wine
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
        dlls.add(entry.dll)
    return dlls


def _extract_from_egg(toc):
    """
    Ensure all binary modules in zipped eggs get extracted and
    included with the frozen executable.

    return  modified table of content
    """
    new_toc = []
    for item in toc:
        # Item is a tupple
        #  (mod_name, path, type)
        modname, pth, typ = item
        if not os.path.isfile(pth):
            pth = check_extract_from_egg(pth)[0][0]

        # Add value to new data structure.
        new_toc.append((modname, pth, typ))
    return new_toc


def Dependencies(lTOC, xtrapath=None, manifest=None):
    """
    Expand LTOC to include all the closure of binary dependencies.

    LTOC is a logical table of contents, ie, a seq of tuples (name, path).
    Return LTOC expanded by all the binary dependencies of the entries
    in LTOC, except those listed in the module global EXCLUDES

    manifest should be a winmanifest.Manifest instance on Windows, so
    that all dependent assemblies can be added
    """
    # Extract all necessary binary modules from Python eggs to be included
    # directly with PyInstaller.
    lTOC = _extract_from_egg(lTOC)

    for nm, pth, typ in lTOC:
        if seen.get(nm.upper(), 0):
            continue
        logger.debug("Analyzing %s", pth)
        seen[nm.upper()] = 1
        if is_win:
            for ftocnm, fn in selectAssemblies(pth, manifest):
                lTOC.append((ftocnm, fn, 'BINARY'))
        for lib, npth in selectImports(pth, xtrapath):
            if seen.get(lib.upper(), 0) or seen.get(npth.upper(), 0):
                continue
            seen[npth.upper()] = 1
            lTOC.append((lib, npth, 'BINARY'))

    return lTOC


def pkg_resouces_get_default_cache():
    """
    Determine the default cache location

    This returns the ``PYTHON_EGG_CACHE`` environment variable, if set.
    Otherwise, on Windows, it returns a 'Python-Eggs' subdirectory of the
    'Application Data' directory.  On all other systems, it's '~/.python-eggs'.
    """
    # This function borrowed from setuptools/pkg_resources
    egg_cache = compat.getenv('PYTHON_EGG_CACHE')
    if egg_cache is not None:
        return egg_cache

    if os.name != 'nt':
        return os.path.expanduser('~/.python-eggs')

    app_data = 'Application Data'   # XXX this may be locale-specific!
    app_homes = [
        (('APPDATA',), None),       # best option, should be locale-safe
        (('USERPROFILE',), app_data),
        (('HOMEDRIVE', 'HOMEPATH'), app_data),
        (('HOMEPATH',), app_data),
        (('HOME',), None),
        (('WINDIR',), app_data),    # 95/98/ME
    ]

    for keys, subdir in app_homes:
        dirname = ''
        for key in keys:
            if key in os.environ:
                dirname = os.path.join(dirname, compat.getenv(key))
            else:
                break
        else:
            if subdir:
                dirname = os.path.join(dirname, subdir)
            return os.path.join(dirname, 'Python-Eggs')
    else:
        raise RuntimeError(
            "Please set the PYTHON_EGG_CACHE enviroment variable"
        )


def check_extract_from_egg(pth, todir=None):
    r"""
    Check if path points to a file inside a python egg file, extract the
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
                    raise SystemExit("Error: %s %s" % (eggpth, e))
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
    """
    Return the dependent assemblies of a binary.
    """
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
                logger.info('Cannot get manifest resource from non-PE '
                            'file %s', pth)
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
                    logger.error("Can not parse manifest resource %s, %s"
                                 "from %s", name, language, pth)
                    logger.exception(exc)
                else:
                    if manifest.dependentAssemblies:
                        logger.debug("Dependent assemblies of %s:", pth)
                        logger.debug(", ".join([assembly.getid()
                                               for assembly in
                                               manifest.dependentAssemblies]))
                    rv.extend(manifest.dependentAssemblies)
    return rv


def selectAssemblies(pth, manifest=None):
    """
    Return a binary's dependent assemblies files that should be included.

    Return a list of pairs (name, fullpath)
    """
    rv = []
    if manifest:
        _depNames = set([dep.name for dep in manifest.dependentAssemblies])
    for assembly in getAssemblies(pth):
        if seen.get(assembly.getid().upper(), 0):
            continue
        if manifest and not assembly.name in _depNames:
            # Add assembly as dependency to our final output exe's manifest
            logger.info("Adding %s to dependent assemblies "
                        "of final executable", assembly.name)
            manifest.dependentAssemblies.append(assembly)
            _depNames.add(assembly.name)
        if not dylib.include_library(assembly.name):
            logger.debug("Skipping assembly %s", assembly.getid())
            continue
        if assembly.optional:
            logger.debug("Skipping optional assembly %s", assembly.getid())
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
                if not seen.get(fn.upper(), 0):
                    logger.debug("Adding %s", ftocnm)
                    seen[nm.upper()] = 1
                    seen[fn.upper()] = 1
                    rv.append((ftocnm, fn))
                else:
                    #logger.info("skipping %s part of assembly %s dependency of %s",
                    #            ftocnm, assembly.name, pth)
                    pass
        else:
            logger.error("Assembly %s not found", assembly.getid())
    return rv


def selectImports(pth, xtrapath=None):
    """
    Return the dependencies of a binary that should be included.

    Return a list of pairs (name, fullpath)
    """
    rv = []
    if xtrapath is None:
        xtrapath = [os.path.dirname(pth)]
    else:
        assert isinstance(xtrapath, list)
        xtrapath = [os.path.dirname(pth)] + xtrapath  # make a copy
    dlls = getImports(pth)
    for lib in dlls:
        if seen.get(lib.upper(), 0):
            continue
        if not is_win and not is_cygwin:
            # all other platforms
            npth = lib
            lib = os.path.basename(lib)
        else:
            # plain win case
            npth = getfullnameof(lib, xtrapath)

        # now npth is a candidate lib if found
        # check again for excludes but with regex FIXME: split the list
        if npth:
            candidatelib = npth
        else:
            candidatelib = lib

        if not dylib.include_library(candidatelib):
            if (candidatelib.find('libpython') < 0 and
               candidatelib.find('Python.framework') < 0):
                # skip libs not containing (libpython or Python.framework)
                if not seen.get(npth.upper(), 0):
                    logger.debug("Skipping %s dependency of %s",
                                 lib, os.path.basename(pth))
                continue
            else:
                pass

        if npth:
            if not seen.get(npth.upper(), 0):
                logger.debug("Adding %s dependency of %s",
                             lib, os.path.basename(pth))
                rv.append((lib, npth))
        else:
            logger.warning("lib not found: %s dependency of %s", lib, pth)

    return rv


def _getImports_ldd(pth):
    """
    Find the binary dependencies of PTH.

    This implementation is for ldd platforms (mostly unix).
    """
    rslt = set()
    if is_aix:
        # Match libs of the form 'archive.a(sharedobject.so)'
        # Will not match the fake lib '/unix'
        lddPattern = re.compile(r"\s*(.*?)(\(.*\))")
    else:
        lddPattern = re.compile(r"\s*(.*?)\s+=>\s+(.*?)\s+\(.*\)")

    for line in compat.exec_command('ldd', pth).splitlines():
        m = lddPattern.search(line)
        if m:
            if is_aix:
                lib = m.group(1)
                name = os.path.basename(lib) + m.group(2)
            else:
                name, lib = m.group(1), m.group(2)
            if name[:10] in ('linux-gate', 'linux-vdso'):
                # linux-gate is a fake library which does not exist and
                # should be ignored. See also:
                # http://www.trilithium.com/johan/2005/08/linux-gate/
                continue

            if os.path.exists(lib):
                # Add lib if it is not already found.
                if lib not in rslt:
                    rslt.add(lib)
            else:
                logger.error('Can not find %s in path %s (needed by %s)',
                             name, lib, pth)
    return rslt


def _getImports_macholib(pth):
    """
    Find the binary dependencies of PTH.

    This implementation is for Mac OS X and uses library macholib.
    """
    from PyInstaller.lib.macholib.MachO import MachO
    from PyInstaller.lib.macholib.mach_o import LC_RPATH
    from PyInstaller.lib.macholib.dyld import dyld_find
    rslt = set()
    seen = set()  # Libraries read from binary headers.

    ## Walk through mach binary headers.

    m = MachO(pth)
    for header in m.headers:
        for idx, name, lib in header.walkRelocatables():
            # Sometimes some libraries are present multiple times.
            if lib not in seen:
                seen.add(lib)

    # Walk through mach binary headers and look for LC_RPATH.
    # macholib can't handle @rpath. LC_RPATH has to be read
    # from the MachO header.
    # TODO Do we need to remove LC_RPATH from MachO load commands?
    #      Will it cause any harm to leave them untouched?
    #      Removing LC_RPATH should be implemented when getting
    #      files from the bincache if it is necessary.
    run_paths = set()
    for header in m.headers:
        for command in header.commands:
            # A command is a tupple like:
            #   (<macholib.mach_o.load_command object at 0x>,
            #    <macholib.mach_o.rpath_command object at 0x>,
            #    '../lib\x00\x00')
            cmd_type = command[0].cmd
            if cmd_type == LC_RPATH:
                rpath = command[2]
                # Remove trailing '\x00' characters.
                # e.g. '../lib\x00\x00'
                rpath = rpath.rstrip('\x00')
                # Make rpath absolute. According to Apple doc LC_RPATH
                # is always relative to the binary location.
                rpath = os.path.normpath(os.path.join(os.path.dirname(pth), rpath))
                run_paths.update([rpath])

    ## Try to find files in file system.

    # In cases with @loader_path or @executable_path
    # try to look in the same directory as the checked binary is.
    # This seems to work in most cases.
    exec_path = os.path.abspath(os.path.dirname(pth))

    for lib in seen:

        # Suppose that @rpath is not used for system libraries and
        # using macholib can be avoided.
        # macholib can't handle @rpath.
        if lib.startswith('@rpath'):
            lib = lib.replace('@rpath', '.')  # Make path relative.
            final_lib = None  # Absolute path to existing lib on disk.
            # Try multiple locations.
            for run_path in run_paths:
                # @rpath may contain relative value. Use exec_path as
                # base path.
                if not os.path.isabs(run_path):
                    run_path = os.path.join(exec_path, run_path)
                # Stop looking for lib when found in first location.
                if os.path.exists(os.path.join(run_path, lib)):
                    final_lib = os.path.abspath(os.path.join(run_path, lib))
                    rslt.add(final_lib)
                    break
            # Log error if no existing file found.
            if not final_lib:
                logger.error('Can not find path %s (needed by %s)', lib, pth)

        # Macholib has to be used to get absolute path to libraries.
        else:
            # macholib can't handle @loader_path. It has to be
            # handled the same way as @executable_path.
            # It is also replaced by 'exec_path'.
            if lib.startswith('@loader_path'):
                lib = lib.replace('@loader_path', '@executable_path')
            try:
                lib = dyld_find(lib, executable_path=exec_path)
                rslt.add(lib)
            except ValueError:
                logger.error('Can not find path %s (needed by %s)', lib, pth)

    return rslt


def getImports(pth):
    """
    Forwards to the correct getImports implementation for the platform.
    """
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
            if logger.isEnabledFor(logging.WARN):
                 # logg excaption only if level >= warn
                logger.warn('Can not get binary dependencies for file: %s', pth)
                logger.exception(exception)
            return []
    elif is_darwin:
        return _getImports_macholib(pth)
    else:
        return _getImports_ldd(pth)


def findLibrary(name):
    """
    Look for a library in the system.

    Emulate the algorithm used by dlopen.
    `name`must include the prefix, e.g. ``libpython2.4.so``
    """
    assert is_unix, ("Current implementation for Unix only (Linux, Solaris, "
                     "AIX, FreeBSD)")

    lib = None

    # Look in the LD_LIBRARY_PATH according to platform.
    if is_aix:
        lp = compat.getenv('LIBPATH', '')
    elif is_darwin:
        lp = compat.getenv('DYLD_LIBRARY_PATH', '')
    else:
        lp = compat.getenv('LD_LIBRARY_PATH', '')
    for path in lp.split(os.pathsep):
        libs = glob(os.path.join(path, name + '*'))
        if libs:
            lib = libs[0]
            break

    # Look in /etc/ld.so.cache
    # TODO Look for ldconfig in /usr/sbin/ldconfig. /sbin is deprecated
    #      in recent linux distributions.
    # Solaris does not have /sbin/ldconfig. Just check if this file exists.
    if lib is None and os.path.exists('/sbin/ldconfig'):
        expr = r'/[^\(\)\s]*%s\.[^\(\)\s]*' % re.escape(name)
        if is_freebsd:
            # This has a slightly different format than on linux, but the
            # regex still works.
            m = re.search(expr, compat.exec_command('/sbin/ldconfig', '-r'))
        else:
            m = re.search(expr, compat.exec_command('/sbin/ldconfig', '-p'))

        if m:
            lib = m.group(0)

    # Look in the known safe paths
    if lib is None:
        paths = ['/lib', '/lib32', '/lib64', '/usr/lib', '/usr/lib32', '/usr/lib64']

        # On Debian/Ubuntu /usr/bin/python is linked statically with libpython.
        # Newer Debian/Ubuntu with multiarch support putsh the libpythonX.Y.so
        # To paths like /usr/lib/i386-linux-gnu/.
        try:
            import sysconfig  # Module available only in Python 2.7.
            arch_subdir = sysconfig.get_config_var('multiarchsubdir')
            # Ignore if None is returned.
            if arch_subdir:
                arch_subdir = os.path.basename(arch_subdir)
                paths.extend([
                    os.path.join('/usr/lib', arch_subdir),
                    os.path.join('/usr/lib32', arch_subdir),
                    os.path.join('/usr/lib64', arch_subdir),
                ])
        except ImportError:
            pass

        if is_aix:
            paths.append('/opt/freeware/lib')
        elif is_freebsd:
            paths.append('/usr/local/lib')
        for path in paths:
            libs = glob(os.path.join(path, name + '*'))
            if libs:
                lib = libs[0]
                break

    # give up :(
    if lib is None:
        return None

    # Resolve the file name into the soname
    if is_freebsd:
        # On FreeBSD objdump doesn't show SONAME, so we just return the lib
        # we've found
        return lib
    else:
        dir = os.path.dirname(lib)
        return os.path.join(dir, getSoname(lib))


def getSoname(filename):
    """
    Return the soname of a library.
    """
    cmd = ["objdump", "-p", "-j", ".dynamic", filename]
    m = re.search(r'\s+SONAME\s+([^\s]+)', compat.exec_command(*cmd))
    if m:
        return m.group(1)


def get_python_library_path():
    """
    Find dynamic Python library that will be bundled with frozen executable.

    Return  full path to Python dynamic library or None when not found.


    We need to know name of the Python dynamic library for the bootloader.
    Bootloader has to know what library to load and not trying to guess.

    Some linux distributions (e.g. debian-based) statically build the
    Python executable to the libpython, so bindepend doesn't include
    it in its output. In this situation let's try to find it.

    Darwin custom builds could possibly also have non-framework style libraries,
    so this method also checks for that variant as well.
    """
    pyver = sys.version_info[:2]

    if is_win:
        names = ('python%d%d.dll' % pyver,)
    elif is_cygwin:
        names = ('libpython%d%d.dll' % pyver,)
    elif is_darwin:
        names = ('Python', '.Python', 'libpython%d.%d.dylib' % pyver)
    elif is_aix:
        # Shared libs on AIX are archives with shared object members, thus the ".a" suffix.
        names = ('libpython%d.%d.a' % pyver,)
    elif is_freebsd:
        names = ('libpython%d.%d.so.1' % pyver,)
    elif is_unix:
        # Other *nix platforms.
        names = ('libpython%d.%d.so.1.0' % pyver,)
    else:
        raise SystemExit('Your platform is not yet supported.')

    # Try to get Python library name from the Python executable. It assumes that Python
    # library is not statically linked.
    dlls = getImports(sys.executable)
    for filename in dlls:
        for name in names:
            if os.path.basename(filename) == name:
                # On Windows filename is just like 'python27.dll'. Convert it
                # to absolute path.
                if is_win and not os.path.isabs(filename):
                    filename = getfullnameof(filename)
                # Python library found. Return absolute path to it.
                return filename

    # Python library NOT found. Resume searching using alternative methods.
    # Applies only to non Windows platforms.

    if is_unix:
        for name in names:
            python_libname = findLibrary(name)
            if python_libname:
                return python_libname

    elif is_darwin:
        # On MacPython, Analysis.assemble is able to find the libpython with
        # no additional help, asking for sys.executable dependencies.
        # However, this fails on system python, because the shared library
        # is not listed as a dependency of the binary (most probably it's
        # opened at runtime using some dlopen trickery).
        # This happens on Mac OS X when Python is compiled as Framework.

        # Python compiled as Framework contains same values in sys.prefix
        # and exec_prefix. That's why we can use just sys.prefix.
        # In virtualenv PyInstaller is not able to find Python library.
        # We need special care for this case.
        if compat.is_virtualenv:
            py_prefix = compat.venv_real_prefix
        else:
            py_prefix = sys.prefix

        for name in names:
            full_path = os.path.join(py_prefix, name)
            if os.path.exists(full_path):
                return full_path

    # Python library NOT found. Return just None.
    return None
