#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------



#--- functions for checking guts ---
# NOTE: By GUTS it is meant intermediate files and data structures that
# PyInstaller creates for bundling files and creating final executable.
import glob
import hashlib
import os
import os.path
import pkgutil
import platform
import shutil
import sys

import struct

from PyInstaller.config import CONF
from .. import compat
from ..compat import is_darwin, is_win, EXTENSION_SUFFIXES, \
    open_file, is_py3, is_py37
from ..depend import dylib
from ..depend.bindepend import match_binding_redirect
from ..utils import misc
from ..utils.misc import load_py_data_struct, save_py_data_struct
from .. import log as logging

if is_win:
    from ..utils.win32 import winmanifest, winresource

logger = logging.getLogger(__name__)


#-- Helpers for checking guts.
#
# NOTE: By _GUTS it is meant intermediate files and data structures that
# PyInstaller creates for bundling files and creating final executable.

def _check_guts_eq(attr, old, new, last_build):
    """
    rebuild is required if values differ
    """
    if old != new:
        logger.info("Building because %s changed", attr)
        return True
    return False


def _check_guts_toc_mtime(attr, old, toc, last_build, pyc=0):
    """
    rebuild is required if mtimes of files listed in old toc are newer
    than last_build

    if pyc=1, check for .py files, too

    Use this for calculated/analysed values read from cache.
    """
    for (nm, fnm, typ) in old:
        if misc.mtime(fnm) > last_build:
            logger.info("Building because %s changed", fnm)
            return True
        elif pyc and misc.mtime(fnm[:-1]) > last_build:
            logger.info("Building because %s changed", fnm[:-1])
            return True
    return False


def _check_guts_toc(attr, old, toc, last_build, pyc=0):
    """
    rebuild is required if either toc content changed or mtimes of
    files listed in old toc are newer than last_build

    if pyc=1, check for .py files, too

    Use this for input parameters.
    """
    return (_check_guts_eq(attr, old, toc, last_build)
            or _check_guts_toc_mtime(attr, old, toc, last_build, pyc=pyc))


#---

def add_suffix_to_extensions(toc):
    """
    Returns a new TOC with proper library suffix for EXTENSION items.
    """
    # TODO: Fix this recursive import
    from .datastruct import TOC
    new_toc = TOC()
    for inm, fnm, typ in toc:
        if typ == 'EXTENSION':
            if is_py3:
                # Change the dotted name into a relative path. This places C
                # extensions in the Python-standard location. This only works
                # in Python 3; see comments above
                # ``sys.meta_path.append(CExtensionImporter())`` in
                # ``pyimod03_importers``.
                inm = inm.replace('.', os.sep)
            # In some rare cases extension might already contain a suffix.
            # Skip it in this case.
            if os.path.splitext(inm)[1] not in EXTENSION_SUFFIXES:
                # Determine the base name of the file.
                if is_py3:
                    base_name = os.path.basename(inm)
                else:
                    base_name = inm.rsplit('.')[-1]
                assert '.' not in base_name
                # Use this file's existing extension. For extensions such as
                # ``libzmq.cp36-win_amd64.pyd``, we can't use
                # ``os.path.splitext``, which would give only the ```.pyd`` part
                # of the extension.
                inm = inm + os.path.basename(fnm)[len(base_name):]

        elif typ == 'DEPENDENCY':
            # Use the suffix from the filename.
            # TODO Verify what extensions are by DEPENDENCIES.
            binext = os.path.splitext(fnm)[1]
            if not os.path.splitext(inm)[1] == binext:
                inm = inm + binext
        new_toc.append((inm, fnm, typ))
    return new_toc

def applyRedirects(manifest, redirects):
    """
    Apply the binding redirects specified by 'redirects' to the dependent assemblies
    of 'manifest'.

    :param manifest:
    :type manifest:
    :param redirects:
    :type redirects:
    :return:
    :rtype:
    """
    redirecting = False
    for binding in redirects:
        for dep in manifest.dependentAssemblies:
            if match_binding_redirect(dep, binding):
                logger.info("Redirecting %s version %s -> %s",
                            binding.name, dep.version, binding.newVersion)
                dep.version = binding.newVersion
                redirecting = True
    return redirecting

def checkCache(fnm, strip=False, upx=False, dist_nm=None):
    """
    Cache prevents preprocessing binary files again and again.

    'dist_nm'  Filename relative to dist directory. We need it on Mac
               to determine level of paths for @loader_path like
               '@loader_path/../../' for qt4 plugins.
    """
    from ..config import CONF
    # On darwin a cache is required anyway to keep the libaries
    # with relative install names. Caching on darwin does not work
    # since we need to modify binary headers to use relative paths
    # to dll depencies and starting with '@loader_path'.
    if not strip and not upx and not is_darwin and not is_win:
        return fnm

    if dist_nm is not None and ":" in dist_nm:
        # A file embedded in another pyinstaller build via multipackage
        # No actual file exists to process
        return fnm

    if strip:
        strip = True
    else:
        strip = False
    if upx:
        upx = True
    else:
        upx = False

    # Load cache index
    # Make cachedir per Python major/minor version.
    # This allows parallel building of executables with different
    # Python versions as one user.
    pyver = ('py%d%s') % (sys.version_info[0], sys.version_info[1])
    arch = platform.architecture()[0]
    cachedir = os.path.join(CONF['cachedir'], 'bincache%d%d_%s_%s' % (strip, upx, pyver, arch))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    cacheindexfn = os.path.join(cachedir, "index.dat")
    if os.path.exists(cacheindexfn):
        try:
            cache_index = load_py_data_struct(cacheindexfn)
        except Exception as e:
            # tell the user they may want to fix their cache
            # .. however, don't delete it for them; if it keeps getting
            #    corrupted, we'll never find out
            logger.warn("pyinstaller bincache may be corrupted; "
                        "use pyinstaller --clean to fix")
            raise
    else:
        cache_index = {}

    # Verify if the file we're looking for is present in the cache.
    # Use the dist_mn if given to avoid different extension modules
    # sharing the same basename get corrupted.
    if dist_nm:
        basenm = os.path.normcase(dist_nm)
    else:
        basenm = os.path.normcase(os.path.basename(fnm))

    # Binding redirects should be taken into account to see if the file
    # needs to be reprocessed. The redirects may change if the versions of dependent
    # manifests change due to system updates.
    redirects = CONF.get('binding_redirects', [])
    digest = cacheDigest(fnm, redirects)
    cachedfile = os.path.join(cachedir, basenm)
    cmd = None
    if basenm in cache_index:
        if digest != cache_index[basenm]:
            os.remove(cachedfile)
        else:
            # On Mac OS X we need relative paths to dll dependencies
            # starting with @executable_path
            if is_darwin:
                dylib.mac_set_relative_dylib_deps(cachedfile, dist_nm)
            return cachedfile


    # Optionally change manifest and its deps to private assemblies
    if fnm.lower().endswith(".manifest"):
        manifest = winmanifest.Manifest()
        manifest.filename = fnm
        with open(fnm, "rb") as f:
            manifest.parse_string(f.read())
        if CONF.get('win_private_assemblies', False):
            if manifest.publicKeyToken:
                logger.info("Changing %s into private assembly", os.path.basename(fnm))
            manifest.publicKeyToken = None
            for dep in manifest.dependentAssemblies:
                # Exclude common-controls which is not bundled
                if dep.name != "Microsoft.Windows.Common-Controls":
                    dep.publicKeyToken = None

        applyRedirects(manifest, redirects)

        manifest.writeprettyxml(cachedfile)
        return cachedfile

    if upx:
        if strip:
            fnm = checkCache(fnm, strip=True, upx=False)
        bestopt = "--best"
        # FIXME: Linux builds of UPX do not seem to contain LZMA (they assert out)
        # A better configure-time check is due.
        if CONF["hasUPX"] >= (3,) and os.name == "nt":
            bestopt = "--lzma"

        upx_executable = "upx"
        if CONF.get('upx_dir'):
            upx_executable = os.path.join(CONF['upx_dir'], upx_executable)
        cmd = [upx_executable, bestopt, "-q", cachedfile]
    else:
        if strip:
            strip_options = []
            if is_darwin:
                # The default strip behaviour breaks some shared libraries
                # under Mac OSX.
                # -S = strip only debug symbols.
                strip_options = ["-S"]
            cmd = ["strip"] + strip_options + [cachedfile]

    if not os.path.exists(os.path.dirname(cachedfile)):
        os.makedirs(os.path.dirname(cachedfile))
    # There are known some issues with 'shutil.copy2' on Mac OS X 10.11
    # with copying st_flags. Issue #1650.
    # 'shutil.copy' copies also permission bits and it should be sufficient for
    # PyInstalle purposes.
    shutil.copy(fnm, cachedfile)
    # TODO find out if this is still necessary when no longer using shutil.copy2()
    if hasattr(os, 'chflags'):
        # Some libraries on FreeBSD have immunable flag (libthr.so.3, for example)
        # If flags still remains, os.chmod will failed with:
        # OSError: [Errno 1] Operation not permitted.
        try:
            os.chflags(cachedfile, 0)
        except OSError:
            pass
    os.chmod(cachedfile, 0o755)

    if os.path.splitext(fnm.lower())[1] in (".pyd", ".dll"):
        # When shared assemblies are bundled into the app, they may optionally be
        # changed into private assemblies.
        try:
            res = winmanifest.GetManifestResources(os.path.abspath(cachedfile))
        except winresource.pywintypes.error as e:
            if e.args[0] == winresource.ERROR_BAD_EXE_FORMAT:
                # Not a win32 PE file
                pass
            else:
                logger.error(os.path.abspath(cachedfile))
                raise
        else:
            if winmanifest.RT_MANIFEST in res and len(res[winmanifest.RT_MANIFEST]):
                for name in res[winmanifest.RT_MANIFEST]:
                    for language in res[winmanifest.RT_MANIFEST][name]:
                        try:
                            manifest = winmanifest.Manifest()
                            manifest.filename = ":".join([cachedfile,
                                                          str(winmanifest.RT_MANIFEST),
                                                          str(name),
                                                          str(language)])
                            manifest.parse_string(res[winmanifest.RT_MANIFEST][name][language],
                                                  False)
                        except Exception as exc:
                            logger.error("Cannot parse manifest resource %s, "
                                         "%s", name, language)
                            logger.error("From file %s", cachedfile, exc_info=1)
                        else:
                            # optionally change manifest to private assembly
                            private = CONF.get('win_private_assemblies', False)
                            if private:
                                if manifest.publicKeyToken:
                                    logger.info("Changing %s into a private assembly",
                                                os.path.basename(fnm))
                                manifest.publicKeyToken = None

                                # Change dep to private assembly
                                for dep in manifest.dependentAssemblies:
                                    # Exclude common-controls which is not bundled
                                    if dep.name != "Microsoft.Windows.Common-Controls":
                                        dep.publicKeyToken = None
                            redirecting = applyRedirects(manifest, redirects)
                            if redirecting or private:
                                try:
                                    manifest.update_resources(os.path.abspath(cachedfile),
                                                              [name],
                                                              [language])
                                except Exception as e:
                                    logger.error(os.path.abspath(cachedfile))
                                    raise

    if cmd:
        try:
            logger.info("Executing - " + ' '.join(cmd))
            compat.exec_command(*cmd)
        except OSError as e:
            raise SystemExit("Execution failed: %s" % e)

    # update cache index
    cache_index[basenm] = digest
    save_py_data_struct(cacheindexfn, cache_index)

    # On Mac OS X we need relative paths to dll dependencies
    # starting with @executable_path
    if is_darwin:
        dylib.mac_set_relative_dylib_deps(cachedfile, dist_nm)
    return cachedfile


def cacheDigest(fnm, redirects):
    hasher = hashlib.md5()
    with open(fnm, "rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024), b""):
            hasher.update(chunk)
    if redirects:
        redirects = str(redirects)
        if is_py3:
            redirects = redirects.encode('utf-8')
        hasher.update(redirects)
    digest = bytearray(hasher.digest())
    return digest


def _check_path_overlap(path):
    """
    Check that path does not overlap with WORKPATH or SPECPATH (i.e.
    WORKPATH and SPECPATH may not start with path, which could be
    caused by a faulty hand-edited specfile)

    Raise SystemExit if there is overlap, return True otherwise
    """
    from ..config import CONF
    specerr = 0
    if CONF['workpath'].startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'WORKPATH (%s)', path, CONF['workpath'])
        specerr += 1
    if CONF['specpath'].startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'SPECPATH (%s)', path, CONF['specpath'])
        specerr += 1
    if specerr:
        raise SystemExit('Error: Please edit/recreate the specfile (%s) '
                         'and set a different output name (e.g. "dist").'
                         % CONF['spec'])
    return True


def _make_clean_directory(path):
    """
    Create a clean directory from the given directory name
    """
    if _check_path_overlap(path):
        if os.path.isdir(path):
            try:
                os.remove(path)
            except OSError:
                _rmtree(path)

        os.makedirs(path)


def _rmtree(path):
    """
    Remove directory and all its contents, but only after user confirmation,
    or if the -y option is set
    """
    from ..config import CONF
    if CONF['noconfirm']:
        choice = 'y'
    elif sys.stdout.isatty():
        choice = compat.stdin_input('WARNING: The output directory "%s" and ALL ITS '
                           'CONTENTS will be REMOVED! Continue? (y/n)' % path)
    else:
        raise SystemExit('Error: The output directory "%s" is not empty. '
                         'Please remove all its contents or use the '
                         '-y option (remove output directory without '
                         'confirmation).' % path)
    if choice.strip().lower() == 'y':
        logger.info('Removing dir %s', path)
        shutil.rmtree(path)
    else:
        raise SystemExit('User aborted')


# TODO Refactor to prohibit empty target directories. As the docstring
#below documents, this function currently permits the second item of each
#2-tuple in "hook.datas" to be the empty string, in which case the target
#directory defaults to the source directory's basename. However, this
#functionality is very fragile and hence bad. Instead:
#
#* An exception should be raised if such item is empty.
#* All hooks currently passing the empty string for such item (e.g.,
#  "hooks/hook-babel.py", "hooks/hook-matplotlib.py") should be refactored
#  to instead pass such basename.
def format_binaries_and_datas(binaries_or_datas, workingdir=None):
    """
    Convert the passed list of hook-style 2-tuples into a returned set of
    `TOC`-style 2-tuples.

    Elements of the passed list are 2-tuples `(source_dir_or_glob, target_dir)`.
    Elements of the returned set are 2-tuples `(target_file, source_file)`.
    For backwards compatibility, the order of elements in the former tuples are
    the reverse of the order of elements in the latter tuples!

    Parameters
    ----------
    binaries_or_datas : list
        List of hook-style 2-tuples (e.g., the top-level `binaries` and `datas`
        attributes defined by hooks) whose:
        * The first element is either:
          * A glob matching only the absolute or relative paths of source
            non-Python data files.
          * The absolute or relative path of a source directory containing only
            source non-Python data files.
        * The second element ist he relative path of the target directory
          into which these source files will be recursively copied.

        If the optional `workingdir` parameter is passed, source paths may be
        either absolute or relative; else, source paths _must_ be absolute.
    workingdir : str
        Optional absolute path of the directory to which all relative source
        paths in the `binaries_or_datas` parameter will be prepended by (and
        hence converted into absolute paths) _or_ `None` if these paths are to
        be preserved as relative. Defaults to `None`.

    Returns
    ----------
    set
        Set of `TOC`-style 2-tuples whose:
        * First element is the absolute or relative path of a target file.
        * Second element is the absolute or relative path of the corresponding
          source file to be copied to this target file.
    """
    toc_datas = set()

    for src_root_path_or_glob, trg_root_dir in binaries_or_datas:
        if not trg_root_dir:
            raise SystemExit("Empty DEST not allowed when adding binary "
                             "and data files. "
                             "Maybe you want to used %r.\nCaused by %r." %
                             (os.curdir, src_root_path_or_glob))
        # Convert relative to absolute paths if required.
        if workingdir and not os.path.isabs(src_root_path_or_glob):
            src_root_path_or_glob = os.path.join(
                workingdir, src_root_path_or_glob)

        # Normalize paths.
        src_root_path_or_glob = os.path.normpath(src_root_path_or_glob)
        if os.path.isfile(src_root_path_or_glob):
            src_root_paths = [src_root_path_or_glob]
        else:
            # List of the absolute paths of all source paths matching the
            # current glob.
            src_root_paths = glob.glob(src_root_path_or_glob)

        if not src_root_paths:
            msg = 'Unable to find "%s" when adding binary and data files.' % (
                src_root_path_or_glob)
            # on Debian/Ubuntu, missing pyconfig.h files can be fixed with
            # installing python-dev
            if src_root_path_or_glob.endswith("pyconfig.h"):
                msg += """This would mean your Python installation doesn't
come with proper library files. This usually happens by missing development
package, or unsuitable build parameters of Python installation.
* On Debian/Ubuntu, you would need to install Python development packages
  * apt-get install python3-dev
  * apt-get install python-dev
* If you're building Python by yourself, please rebuild your Python with
`--enable-shared` (or, `--enable-framework` on Darwin)
"""
            raise SystemExit(msg)

        for src_root_path in src_root_paths:
            if os.path.isfile(src_root_path):
                # Normalizing the result to remove redundant relative
                # paths (e.g., removing "./" from "trg/./file").
                toc_datas.add((
                    os.path.normpath(os.path.join(
                        trg_root_dir, os.path.basename(src_root_path))),
                    os.path.normpath(src_root_path)))
            elif os.path.isdir(src_root_path):
                for src_dir, src_subdir_basenames, src_file_basenames in \
                    os.walk(src_root_path):
                    # Ensure the current source directory is a subdirectory
                    # of the passed top-level source directory. Since
                    # os.walk() does *NOT* follow symlinks by default, this
                    # should be the case. (But let's make sure.)
                    assert src_dir.startswith(src_root_path)

                    # Relative path of the current target directory,
                    # obtained by:
                    #
                    # * Stripping the top-level source directory from the
                    #   current source directory (e.g., removing "/top" from
                    #   "/top/dir").
                    # * Normalizing the result to remove redundant relative
                    #   paths (e.g., removing "./" from "trg/./file").
                    trg_dir = os.path.normpath(os.path.join(
                        trg_root_dir,
                        os.path.relpath(src_dir, src_root_path)))

                    for src_file_basename in src_file_basenames:
                        src_file = os.path.join(src_dir, src_file_basename)
                        if os.path.isfile(src_file):
                            # Normalize the result to remove redundant relative
                            # paths (e.g., removing "./" from "trg/./file").
                            toc_datas.add((
                                os.path.normpath(
                                    os.path.join(trg_dir, src_file_basename)),
                                os.path.normpath(src_file)))

    return toc_datas


def _load_code(modname, filename):
    path_item = os.path.dirname(filename)
    if os.path.basename(filename).startswith('__init__.py'):
        # this is a package
        path_item = os.path.dirname(path_item)
    if os.path.basename(path_item) == '__pycache__':
        path_item = os.path.dirname(path_item)
    importer = pkgutil.get_importer(path_item)
    package, _, modname = modname.rpartition('.')

    if sys.version_info >= (3, 3) and hasattr(importer, 'find_loader'):
        loader, portions = importer.find_loader(modname)
    else:
        loader = importer.find_module(modname)

    logger.debug('Compiling %s', filename)
    if loader and hasattr(loader, 'get_code'):
        return loader.get_code(modname)
    else:
        # Just as ``python foo.bar`` will read and execute statements in
        # ``foo.bar``,  even though it lacks the ``.py`` extension, so
        # ``pyinstaller foo.bar``  should also work. However, Python's import
        # machinery doesn't load files without a ``.py`` extension. So, use
        # ``compile`` instead.
        #
        # On a side note, neither the Python 2 nor Python 3 calls to
        # ``pkgutil`` and ``find_module`` above handle modules ending in
        # ``.pyw``, even though ``imp.find_module`` and ``import <name>`` both
        # work. This code supports ``.pyw`` files.

        # Open the source file in binary mode and allow the `compile()` call to
        # detect the source encoding.
        with open_file(filename, 'rb') as f:
            source = f.read()
        return compile(source, filename, 'exec')

def get_code_object(modname, filename):
    """
    Get the code-object for a module.

    This is a extra-simple version for compiling a module. It's
    not worth spending more effort here, as it is only used in the
    rare case if outXX-Analysis.toc exists, but outXX-PYZ.toc does
    not.
    """

    try:
        if filename in ('-', None):
            # This is a NamespacePackage, modulegraph marks them
            # by using the filename '-'. (But wants to use None,
            # so check for None, too, to be forward-compatible.)
            logger.debug('Compiling namespace package %s', modname)
            txt = '#\n'
            return compile(txt, filename, 'exec')
        else:
            logger.debug('Compiling %s', filename)
            co = _load_code(modname, filename)
            if not co:
                raise ValueError("Module file %s is missing" % filename)
            return co
    except SyntaxError as e:
        print("Syntax error in ", filename)
        print(e.args)
        raise


def strip_paths_in_code(co, new_filename=None):

    # Paths to remove from filenames embedded in code objects
    replace_paths = sys.path + CONF['pathex']
    # Make sure paths end with os.sep
    replace_paths = [os.path.join(f, '') for f in replace_paths]

    if new_filename is None:
        original_filename = os.path.normpath(co.co_filename)
        for f in replace_paths:
            if original_filename.startswith(f):
                new_filename = original_filename[len(f):]
                break

        else:
            return co

    code_func = type(co)

    consts = tuple(
        strip_paths_in_code(const_co, new_filename)
        if isinstance(const_co, code_func) else const_co
        for const_co in co.co_consts
    )

    # co_kwonlyargcount added in some version of Python 3
    if hasattr(co, 'co_kwonlyargcount'):
        return code_func(co.co_argcount, co.co_kwonlyargcount, co.co_nlocals, co.co_stacksize,
                     co.co_flags, co.co_code, consts, co.co_names,
                     co.co_varnames, new_filename, co.co_name,
                     co.co_firstlineno, co.co_lnotab,
                     co.co_freevars, co.co_cellvars)
    else:
        return code_func(co.co_argcount, co.co_nlocals, co.co_stacksize,
                     co.co_flags, co.co_code, consts, co.co_names,
                     co.co_varnames, new_filename, co.co_name,
                     co.co_firstlineno, co.co_lnotab,
                     co.co_freevars, co.co_cellvars)


def fake_pyc_timestamp(buf):
    """
    Reset the timestamp from a .pyc-file header to a fixed value.

    This enables deterministic builds without having to set pyinstaller
    source metadata (mtime) since that changes the pyc-file contents.

    _buf_ must at least contain the full pyc-file header.
    """
    assert buf[:4] == compat.BYTECODE_MAGIC, \
        "Expected pyc magic {}, got {}".format(compat.BYTECODE_MAGIC, buf[:4])
    start, end = 4, 8
    if is_py37:
        # see https://www.python.org/dev/peps/pep-0552/
        (flags,) = struct.unpack_from(">I", buf, 4)
        if flags & 1:
            # We are in the future and hash-based pyc-files are used, so
            # clear "check_source" flag, since there is no source
            buf[4:8] = struct.pack(">I", flags ^ 2)
            return buf
        else:
            # no hash-based pyc-file, timestamp is the next field
            start, end = 8, 12

    ts = b'pyi0'  # So people know where this comes from
    return buf[:start] + ts + buf[end:]
