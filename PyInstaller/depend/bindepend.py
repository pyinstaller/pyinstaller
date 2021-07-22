#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

"""
Find external dependencies of binary libraries.
"""

import ctypes.util
import os
import re
import sys
from glob import glob
# Required for extracting eggs.
import zipfile
import collections

from PyInstaller import compat
from PyInstaller.depend import dylib, utils

from PyInstaller import log as logging
from PyInstaller.utils.win32 import winutils

logger = logging.getLogger(__name__)

seen = set()

# Import windows specific stuff.
if compat.is_win:
    from distutils.sysconfig import get_python_lib
    from PyInstaller.utils.win32 import winmanifest, winresource
    import pefile
    # Do not load all the directories information from the PE file
    pefile.fast_load = True


def getfullnameof(mod, xtrapath=None):
    """
    Return the full path name of MOD.

    MOD is the basename of a dll or pyd.
    XTRAPATH is a path or list of paths to search first.
    Return the full path name of MOD.
    Will search the full Windows search path, as well as sys.path
    """
    pywin32_paths = []
    if compat.is_win:
        pywin32_paths = [os.path.join(get_python_lib(), 'pywin32_system32')]
        if compat.is_venv:
            pywin32_paths.append(
                os.path.join(compat.base_prefix, 'Lib', 'site-packages',
                             'pywin32_system32')
            )

    epath = (sys.path +  # Search sys.path first!
             pywin32_paths +
             winutils.get_system_path() +
             compat.getenv('PATH', '').split(os.pathsep))
    if xtrapath is not None:
        if type(xtrapath) == type(''):
            epath.insert(0, xtrapath)
        else:
            epath = xtrapath + epath
    for p in epath:
        npth = os.path.join(p, mod)
        if os.path.exists(npth) and matchDLLArch(npth):
            return npth
    return ''


def _getImports_pe(pth):
    """
    Find the binary dependencies of PTH.

    This implementation walks through the PE header
    and uses library pefile for that and supports
    32/64bit Windows
    """
    dlls = set()
    # By default library pefile parses all PE information.
    # We are only interested in the list of dependent dlls.
    # Performance is improved by reading only needed information.
    # https://code.google.com/p/pefile/wiki/UsageExamples

    pe = pefile.PE(pth, fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
        ],
        forwarded_exports_only=True,
        import_dllnames_only=True,
        )

    # Some libraries have no other binary dependencies. Use empty list
    # in that case. Otherwise pefile would return None.
    # e.g. C:\windows\system32\kernel32.dll on Wine
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
        dll_str = winutils.convert_dll_name_to_str(entry.dll)
        dlls.add(dll_str)

    # We must also read the exports table to find forwarded symbols:
    # http://blogs.msdn.com/b/oldnewthing/archive/2006/07/19/671238.aspx
    exportSymbols = getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None)
    if exportSymbols:
        for sym in exportSymbols.symbols:
            if sym.forwarder is not None:
                # sym.forwarder is a bytes object. Convert it to a string.
                forwarder = winutils.convert_dll_name_to_str(sym.forwarder)
                # sym.forwarder is for example 'KERNEL32.EnterCriticalSection'
                dll = forwarder.split('.')[0]
                dlls.add(dll + ".dll")

    pe.close()
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


BindingRedirect = collections.namedtuple('BindingRedirect',
                                         'name language arch oldVersion newVersion publicKeyToken')

def match_binding_redirect(manifest, redirect):
    return all([
        manifest.name == redirect.name,
        manifest.version == redirect.oldVersion,
        manifest.language == redirect.language,
        manifest.processorArchitecture == redirect.arch,
        manifest.publicKeyToken == redirect.publicKeyToken,
    ])

_exe_machine_type = None

def matchDLLArch(filename):
    """
    Return True if the DLL given by filename matches the CPU type/architecture of the
    Python process running PyInstaller.

    Always returns True on non-Windows platforms

    :param filename:
    :type filename:
    :return:
    :rtype:
    """
    # TODO: check machine type on other platforms?
    if not compat.is_win:
        return True

    global _exe_machine_type
    try:
        if _exe_machine_type is None:
            pefilename = compat.python_executable  # for exception handling
            exe_pe = pefile.PE(pefilename, fast_load=True)
            _exe_machine_type = exe_pe.FILE_HEADER.Machine
            exe_pe.close()

        pefilename = filename  # for exception handling
        pe = pefile.PE(filename, fast_load=True)
        match_arch = pe.FILE_HEADER.Machine == _exe_machine_type
        pe.close()
    except pefile.PEFormatError as exc:
        raise SystemExit('Can not get architecture from file: %s\n'
                         '  Reason: %s' % (pefilename, exc))
    return match_arch


def Dependencies(lTOC, xtrapath=None, manifest=None, redirects=None):
    """
    Expand LTOC to include all the closure of binary dependencies.

    `LTOC` is a logical table of contents, ie, a seq of tuples (name, path).
    Return LTOC expanded by all the binary dependencies of the entries
    in LTOC, except those listed in the module global EXCLUDES

    `manifest` may be a winmanifest.Manifest instance for a program manifest, so
    that all dependent assemblies of python.exe can be added to the built exe.

    `redirects` may be a list. Any assembly redirects found via policy files will
    be added to the list as BindingRedirect objects so they can later be used
    to modify any manifests that reference the redirected assembly.
    """
    # Extract all necessary binary modules from Python eggs to be included
    # directly with PyInstaller.
    lTOC = _extract_from_egg(lTOC)

    for nm, pth, typ in lTOC:
        if nm.upper() in seen:
            continue
        logger.debug("Analyzing %s", pth)
        seen.add(nm.upper())
        if compat.is_win:
            for ftocnm, fn in getAssemblyFiles(pth, manifest, redirects):
                lTOC.append((ftocnm, fn, 'BINARY'))
        for lib, npth in selectImports(pth, xtrapath):
            if lib.upper() in seen or npth.upper() in seen:
                continue
            seen.add(npth.upper())
            lTOC.append((lib, npth, 'BINARY'))

    return lTOC


def pkg_resources_get_default_cache():
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
            "Please set the PYTHON_EGG_CACHE environment variable"
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
                except zipfile.BadZipfile as e:
                    raise SystemExit("Error: %s %s" % (eggpth, e))
                if todir is None:
                    # Use the same directory as setuptools/pkg_resources. So,
                    # if the specific egg was accessed before (not necessarily
                    # by pyinstaller), the extracted contents already exist
                    # (pkg_resources puts them there) and can be used.
                    todir = os.path.join(pkg_resources_get_default_cache(),
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
                        with open(pth, "wb") as f:
                            f.write(egg.read(member))
                    rv.append((pth, eggpth, member))
                return rv
    return [(pth, None, None)]


def getAssemblies(pth):
    """
    On Windows return the dependent Side-by-Side (SxS) assemblies of a binary as a
    list of Manifest objects.

    Dependent assemblies are required only by binaries compiled with MSVC 9.0.
    Python 2.7 and 3.2 is compiled with MSVC 9.0 and thus depends on Microsoft
    Redistributable runtime libraries 9.0.

    Python 3.3+ is compiled with version 10.0 and does not use SxS assemblies.

    FIXME: Can this be removed since we now only support Python 3.5+?
    FIXME: IS there some test-case covering this?
    """
    if pth.lower().endswith(".manifest"):
        return []
    # check for manifest file
    manifestnm = pth + ".manifest"
    if os.path.isfile(manifestnm):
        with open(manifestnm, "rb") as fd:
            res = {winmanifest.RT_MANIFEST: {1: {0: fd.read()}}}
    else:
        # check the binary for embedded manifest
        try:
            res = winmanifest.GetManifestResources(pth)
        except winresource.pywintypes.error as exc:
            if exc.args[0] == winresource.ERROR_BAD_EXE_FORMAT:
                logger.info('Cannot get manifest resource from non-PE '
                            'file %s', pth)
                return []
            raise
    rv = []
    if winmanifest.RT_MANIFEST in res and len(res[winmanifest.RT_MANIFEST]):
        for name in res[winmanifest.RT_MANIFEST]:
            for language in res[winmanifest.RT_MANIFEST][name]:
                # check the manifest for dependent assemblies
                try:
                    manifest = winmanifest.Manifest()
                    manifest.filename = ":".join([
                        pth, str(winmanifest.RT_MANIFEST),
                        str(name), str(language),
                    ])
                    manifest.parse_string(
                        res[winmanifest.RT_MANIFEST][name][language], False)
                except Exception as exc:
                    logger.error("Can not parse manifest resource %s, %s"
                                 " from %s", name, language, pth, exc_info=1)
                else:
                    if manifest.dependentAssemblies:
                        logger.debug("Dependent assemblies of %s:", pth)
                        logger.debug(", ".join([assembly.getid()
                                               for assembly in
                                               manifest.dependentAssemblies]))
                    rv.extend(manifest.dependentAssemblies)
    return rv


def getAssemblyFiles(pth, manifest=None, redirects=None):
    """
    Find all assemblies that are dependencies of the given binary and return the files
    that make up the assemblies as (name, fullpath) tuples.

    If a WinManifest object is passed as `manifest`, also updates that manifest to
    reference the returned assemblies. This is done only to update the built app's .exe
    with the dependencies of python.exe

    If a list is passed as `redirects`, and binding redirects in policy files are
    applied when searching for assemblies, BindingRedirect objects are appended to this
    list.

    Return a list of pairs (name, fullpath)
    """
    rv = []
    if manifest:
        _depNames = set(dep.name for dep in manifest.dependentAssemblies)
    for assembly in getAssemblies(pth):
        if assembly.getid().upper() in seen:
            continue
        if manifest and assembly.name not in _depNames:
            # Add assembly as dependency to our final output exe's manifest
            logger.info("Adding %s to dependent assemblies "
                        "of final executable\n  required by %s",
                        assembly.name, pth)
            manifest.dependentAssemblies.append(assembly)
            _depNames.add(assembly.name)
        if not dylib.include_library(assembly.name):
            logger.debug("Skipping assembly %s", assembly.getid())
            continue
        if assembly.optional:
            logger.debug("Skipping optional assembly %s", assembly.getid())
            continue

        from PyInstaller.config import CONF
        if CONF.get("win_no_prefer_redirects"):
            files = assembly.find_files()
        else:
            files = []
        if not len(files):
            # If no files were found, it may be the case that the required version
            # of the assembly is not installed, and the policy file is redirecting it
            # to a newer version. So, we collect the newer version instead.
            files = assembly.find_files(ignore_policies=False)
            if len(files) and redirects is not None:
                # New version was found, old version was not. Add a redirect in the
                # app configuration
                old_version = assembly.version
                new_version = assembly.get_policy_redirect()
                logger.info("Adding redirect %s version %s -> %s",
                            assembly.name, old_version, new_version)
                redirects.append(BindingRedirect(
                    name=assembly.name,
                    language=assembly.language,
                    arch=assembly.processorArchitecture,
                    publicKeyToken=assembly.publicKeyToken,
                    oldVersion=old_version,
                    newVersion=new_version,
                ))

        if files:
            seen.add(assembly.getid().upper())
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
                if fn.upper() not in seen:
                    logger.debug("Adding %s", ftocnm)
                    seen.add(nm.upper())
                    seen.add(fn.upper())
                    rv.append((ftocnm, fn))
                else:
                    #logger.info("skipping %s part of assembly %s dependency of %s",
                    #            ftocnm, assembly.name, pth)
                    pass
        else:
            logger.error("Assembly %s not found", assembly.getid())

    # Convert items in list from 'bytes' type to 'str' type.
    # NOTE: With Python 3 we somehow get type 'bytes' and it
    #       then causes other issues and failures with PyInstaller.
    new_rv = []
    for item in rv:
        a = item[0].decode('ascii')
        b = item[1].decode('ascii')
        new_rv.append((a, b))
    rv = new_rv

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
        if lib.upper() in seen:
            continue
        if not compat.is_win:
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
                if npth.upper() not in seen:
                    logger.debug("Skipping %s dependency of %s",
                                 lib, os.path.basename(pth))
                continue
            else:
                pass

        if npth:
            if npth.upper() not in seen:
                logger.debug("Adding %s dependency of %s from %s",
                             lib, os.path.basename(pth), npth)
                rv.append((lib, npth))
        elif dylib.warn_missing_lib(lib):
            logger.warning("lib not found: %s dependency of %s", lib, pth)

    return rv


def _getImports_ldd(pth):
    """
    Find the binary dependencies of PTH.

    This implementation is for ldd platforms (mostly unix).
    """
    rslt = set()
    if compat.is_aix:
        # Match libs of the form
        #   'archivelib.a(objectmember.so/.o)'
        # or
        #   'sharedlib.so'
        # Will not match the fake lib '/unix'
        lddPattern = re.compile(r"^\s*(((?P<libarchive>(.*\.a))(?P<objectmember>\(.*\)))|((?P<libshared>(.*\.so))))$")
    elif compat.is_hpux:
        # Match libs of the form
        #   'sharedlib.so => full-path-to-lib
        # e.g.
        #   'libpython2.7.so =>      /usr/local/lib/hpux32/libpython2.7.so'
        lddPattern = re.compile(r"^\s+(.*)\s+=>\s+(.*)$")
    elif compat.is_solar:
        # Match libs of the form
        #   'sharedlib.so => full-path-to-lib
        # e.g.
        #   'libpython2.7.so.1.0 => /usr/local/lib/libpython2.7.so.1.0'
        # Will not match the platform specific libs starting with '/platform'
        lddPattern = re.compile(r"^\s+(.*)\s+=>\s+(.*)$")
    else:
        lddPattern = re.compile(r"\s*(.*?)\s+=>\s+(.*?)\s+\(.*\)")

    for line in compat.exec_command('ldd', pth).splitlines():
        m = lddPattern.search(line)
        if m:
            if compat.is_aix:
                libarchive = m.group('libarchive')
                if libarchive:
                    # We matched an archive lib with a request for a particular
                    # embedded shared object.
                    #   'archivelib.a(objectmember.so/.o)'
                    lib = libarchive
                    name = os.path.basename(lib) + m.group('objectmember')
                else:
                    # We matched a stand-alone shared library.
                    #   'sharedlib.so'
                    lib = m.group('libshared')
                    name = os.path.basename(lib)
            elif compat.is_hpux:
                name, lib = m.group(1), m.group(2)
            else:
                name, lib = m.group(1), m.group(2)
            if name[:10] in ('linux-gate', 'linux-vdso'):
                # linux-gate is a fake library which does not exist and
                # should be ignored. See also:
                # http://www.trilithium.com/johan/2005/08/linux-gate/
                continue

            if compat.is_cygwin:
                # exclude Windows system library
                if lib.lower().startswith('/cygdrive/c/windows/system'):
                    continue

            if os.path.exists(lib):
                # Add lib if it is not already found.
                if lib not in rslt:
                    rslt.add(lib)
            elif dylib.warn_missing_lib(name):
                logger.warning('Cannot find %s in path %s (needed by %s)',
                               name, lib, pth)
        elif line.endswith("not found"):
            # On glibc-based linux distributions, missing libraries
            # are marked with name.so => not found
            tokens = line.split('=>')
            if len(tokens) != 2:
                continue
            name = tokens[0].strip()
            if dylib.warn_missing_lib(name):
                logger.warning('Cannot find %s (needed by %s)', name, pth)
    return rslt


def _getImports_macholib(pth):
    """
    Find the binary dependencies of PTH.

    This implementation is for Mac OS X and uses library macholib.
    """
    from macholib.MachO import MachO
    from macholib.mach_o import LC_RPATH
    from macholib.dyld import dyld_find
    from macholib.util import in_system_path
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
                rpath = command[2].decode('utf-8')
                # Remove trailing '\x00' characters.
                # e.g. '../lib\x00\x00'
                rpath = rpath.rstrip('\x00')
                # Replace the @executable_path and @loader_path keywords
                # with the actual path to the binary.
                executable_path = os.path.dirname(pth)
                rpath = re.sub('^@(executable_path|loader_path|rpath)(/|$)',
                               executable_path + r'\2', rpath)
                # Make rpath absolute. According to Apple doc LC_RPATH
                # is always relative to the binary location.
                rpath = os.path.normpath(os.path.join(executable_path, rpath))
                run_paths.update([rpath])
            else:
                # Frameworks that have this structure Name.framework/Versions/N/Name
                # need to to search at the same level as the framework dir.
                # This is specifically needed so that the QtWebEngine dependencies
                # can be found.
                if '.framework' in pth:
                    run_paths.update(['../../../'])

    # for distributions like Anaconda, all of the dylibs are stored in the lib directory
    # of the Python distribution, not alongside of the .so's in each module's subdirectory.
    run_paths.add(os.path.join(compat.base_prefix, 'lib'))

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
            # Log warning if no existing file found.
            if not final_lib and dylib.warn_missing_lib(lib):
                logger.warning('Cannot find path %s (needed by %s)', lib, pth)

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
                # Starting with Big Sur, system libraries are hidden. And
                # we do not collect system libraries on any macOS version
                # anyway, so suppress the corresponding error messages.
                if not in_system_path(lib) and dylib.warn_missing_lib(lib):
                    logger.warning('Cannot find path %s (needed by %s)',
                                   lib, pth)

    return rslt


def getImports(pth):
    """
    Forwards to the correct getImports implementation for the platform.
    """
    if compat.is_win:
        if pth.lower().endswith(".manifest"):
            return []
        try:
            return _getImports_pe(pth)
        except Exception as exception:
            # Assemblies can pull in files which aren't necessarily PE,
            # but are still needed by the assembly. Any additional binary
            # dependencies should already have been handled by
            # selectAssemblies in that case, so just warn, return an empty
            # list and continue.
            # For less specific errors also log the traceback.
            logger.warning('Can not get binary dependencies for file: %s', pth)
            logger.warning(
                '  Reason: %s', exception,
                exc_info=not isinstance(exception, pefile.PEFormatError))
            return []
    elif compat.is_darwin:
        return _getImports_macholib(pth)
    else:
        return _getImports_ldd(pth)


def findLibrary(name):
    """
    Look for a library in the system.

    Emulate the algorithm used by dlopen.
    `name`must include the prefix, e.g. ``libpython2.4.so``
    """
    assert compat.is_unix, \
        "Current implementation for Unix only (Linux, Solaris, AIX, FreeBSD)"

    lib = None

    # Look in the LD_LIBRARY_PATH according to platform.
    if compat.is_aix:
        lp = compat.getenv('LIBPATH', '')
    elif compat.is_darwin:
        lp = compat.getenv('DYLD_LIBRARY_PATH', '')
    else:
        lp = compat.getenv('LD_LIBRARY_PATH', '')
    for path in lp.split(os.pathsep):
        libs = glob(os.path.join(path, name + '*'))
        if libs:
            lib = libs[0]
            break

    # Look in /etc/ld.so.cache
    # Solaris does not have /sbin/ldconfig. Just check if this file exists.
    if lib is None:
        utils.load_ldconfig_cache()
        lib = utils.LDCONFIG_CACHE.get(name)
        if lib:
            assert os.path.isfile(lib)

    # Look in the known safe paths.
    if lib is None:
        # Architecture independent locations.
        paths = ['/lib', '/usr/lib']
        # Architecture dependent locations.
        if compat.architecture == '32bit':
            paths.extend(['/lib32', '/usr/lib32', '/usr/lib/i386-linux-gnu'])
        else:
            paths.extend(['/lib64', '/usr/lib64', '/usr/lib/x86_64-linux-gnu'])


        # On Debian/Ubuntu /usr/bin/python is linked statically with libpython.
        # Newer Debian/Ubuntu with multiarch support putsh the libpythonX.Y.so
        # To paths like /usr/lib/i386-linux-gnu/.
        try:
            # Module available only in Python 2.7+
            import sysconfig
            # 'multiarchsubdir' works on Debian/Ubuntu only in Python 2.7 and 3.3+.
            arch_subdir = sysconfig.get_config_var('multiarchsubdir')
            # Ignore if None is returned.
            if arch_subdir:
                arch_subdir = os.path.basename(arch_subdir)
                paths.append(os.path.join('/usr/lib', arch_subdir))
            else:
                logger.debug('Multiarch directory not detected.')
        except ImportError:
            logger.debug('Multiarch directory not detected.')

        if compat.is_aix:
            paths.append('/opt/freeware/lib')
        elif compat.is_hpux:
            if compat.architecture == '32bit':
                paths.append('/usr/local/lib/hpux32')
            else:
                paths.append('/usr/local/lib/hpux64')
        elif compat.is_freebsd or compat.is_openbsd:
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
    if compat.is_freebsd or compat.is_aix or compat.is_openbsd:
        # On FreeBSD objdump doesn't show SONAME,
        # and on AIX objdump does not exist,
        # so we just return the lib we've found
        return lib
    else:
        dir = os.path.dirname(lib)
        return os.path.join(dir, _get_so_name(lib))


def _get_so_name(filename):
    """
    Return the soname of a library.

    Soname is usefull whene there are multiple symplinks to one library.
    """
    # TODO verify that objdump works on other unixes and not Linux only.
    cmd = ["objdump", "-p", filename]
    pattern = r'\s+SONAME\s+([^\s]+)'
    if compat.is_solar:
        cmd = ["elfdump", "-d", filename]
        pattern = r'\s+SONAME\s+[^\s]+\s+([^\s]+)'
    m = re.search(pattern, compat.exec_command(*cmd))
    return m.group(1)


def get_python_library_path():
    """
    Find dynamic Python library that will be bundled with frozen executable.

    NOTOE: This is a fallback option when Python library is probably linked
    statically with the Python executable and we need to search more for it.
    On Debian/Ubuntu this is the case.

    Return  full path to Python dynamic library or None when not found.


    We need to know name of the Python dynamic library for the bootloader.
    Bootloader has to know what library to load and not trying to guess.

    Some linux distributions (e.g. debian-based) statically build the
    Python executable to the libpython, so bindepend doesn't include
    it in its output. In this situation let's try to find it.

    Darwin custom builds could possibly also have non-framework style libraries,
    so this method also checks for that variant as well.
    """
    def _find_lib_in_libdirs(*libdirs):
        for libdir in libdirs:
            for name in compat.PYDYLIB_NAMES:
                full_path = os.path.join(libdir, name)
                if os.path.exists(full_path):
                    return full_path
        return None

    # If this is Microsoft App Store Python, check the compat.base_path first.
    # While compat.python_executable resolves to actual python.exe file, the
    # latter contains relative library reference that does not get properly
    # resolved by getfullnameof().
    if compat.is_ms_app_store:
        python_libname = _find_lib_in_libdirs(compat.base_prefix)
        if python_libname:
            return python_libname

    # Try to get Python library name from the Python executable. It assumes that Python
    # library is not statically linked.
    dlls = getImports(compat.python_executable)
    for filename in dlls:
        for name in compat.PYDYLIB_NAMES:
            if os.path.basename(filename) == name:
                # On Windows filename is just like 'python27.dll'. Convert it
                # to absolute path.
                if compat.is_win and not os.path.isabs(filename):
                    filename = getfullnameof(filename)
                # Python library found. Return absolute path to it.
                return filename

    # Python library NOT found. Resume searching using alternative methods.

    # Work around for python venv having VERSION.dll rather than pythonXY.dll
    if compat.is_win and 'VERSION.dll' in dlls:
        pydll = 'python%d%d.dll' % sys.version_info[:2]
        return getfullnameof(pydll)

    # Applies only to non Windows platforms and conda.

    if compat.is_conda:
        # Conda needs to be the first here since it overrules the operating
        # system specific paths.
        python_libname = _find_lib_in_libdirs(
            os.path.join(compat.base_prefix, 'lib'))
        if python_libname:
            return python_libname

    elif compat.is_unix:
        for name in compat.PYDYLIB_NAMES:
            python_libname = findLibrary(name)
            if python_libname:
                return python_libname

    elif compat.is_darwin:
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
        python_libname = _find_lib_in_libdirs(
            compat.base_prefix,
            os.path.join(compat.base_prefix, 'lib'))
        if python_libname:
            return python_libname

    # Python library NOT found. Provide helpful feedback.
    msg = """Python library not found: %s
    This would mean your Python installation doesn't come with proper library files.
    This usually happens by missing development package, or unsuitable build parameters of Python installation.

    * On Debian/Ubuntu, you would need to install Python development packages
      * apt-get install python3-dev
      * apt-get install python-dev
    * If you're building Python by yourself, please rebuild your Python with `--enable-shared` (or, `--enable-framework` on Darwin)
    """ % (", ".join(compat.PYDYLIB_NAMES),)
    raise IOError(msg)


def findSystemLibrary(name):
    '''
        Given a library name, try to resolve the path to that library. If the
        path is already an absolute path, return that without searching.
    '''

    if os.path.isabs(name):
        return name

    if compat.is_unix:
        return findLibrary(name)
    elif compat.is_win:
        return getfullnameof(name)
    else:
        # This seems to work, and is similar to what we have above..
        return ctypes.util.find_library(name)
