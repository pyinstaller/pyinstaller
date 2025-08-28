#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import fnmatch
import glob
import hashlib
import io
import marshal
import os
import pathlib
import platform
import shutil
import struct
import subprocess
import sys
import types
import zipfile

from PyInstaller import compat
from PyInstaller import log as logging
from PyInstaller.compat import is_aix, is_darwin, is_win, is_linux
from PyInstaller.exceptions import InvalidSrcDestTupleError
from PyInstaller.utils import misc

if is_win:
    from PyInstaller.utils.win32 import versioninfo

if is_darwin:
    import PyInstaller.utils.osx as osxutils

logger = logging.getLogger(__name__)

# -- Helpers for checking guts.
#
# NOTE: by _GUTS it is meant intermediate files and data structures that PyInstaller creates for bundling files and
# creating final executable.


def _check_guts_eq(attr_name, old_value, new_value, last_build):
    """
    Rebuild is required if values differ.
    """
    if old_value != new_value:
        logger.info("Building because %s changed", attr_name)
        return True
    return False


def _check_guts_toc_mtime(attr_name, old_toc, new_toc, last_build):
    """
    Rebuild is required if mtimes of files listed in old TOC are newer than last_build.

    Use this for calculated/analysed values read from cache.
    """
    for dest_name, src_name, typecode in old_toc:
        if misc.mtime(src_name) > last_build:
            logger.info("Building because %s changed", src_name)
            return True
    return False


def _check_guts_toc(attr_name, old_toc, new_toc, last_build):
    """
    Rebuild is required if either TOC content changed or mtimes of files listed in old TOC are newer than last_build.

    Use this for input parameters.
    """
    return _check_guts_eq(attr_name, old_toc, new_toc, last_build) or \
        _check_guts_toc_mtime(attr_name, old_toc, new_toc, last_build)


def destination_name_for_extension(module_name, src_name, typecode):
    """
    Take a TOC entry (dest_name, src_name, typecode) and determine the full destination name for the extension.
    """

    assert typecode == 'EXTENSION'

    # The `module_name` should be the extension's importable module name, such as `psutil._psutil_linux` or
    # `numpy._core._multiarray_umath`. Reconstruct the directory structure from parent package name(s), if any.
    dest_elements = module_name.split('.')

    # We have the base name of the extension file (the last element in the module name), but we do not know the
    # full extension suffix. We can take that from source name; for simplicity, replace the whole base name part.
    src_path = pathlib.Path(src_name)
    dest_elements[-1] = src_path.name

    # Extensions that originate from python's python3.x/lib-dynload directory should be diverted into
    # python3.x/lib-dynload destination directory instead of being collected into top-level application directory.
    # See #5604 for original motivation (using just lib-dynload), and #9204 for extension (using python3.x/lib-dynload).
    if src_path.parent.name == 'lib-dynload':
        python_dir = f'python{sys.version_info.major}.{sys.version_info.minor}'
        if src_path.parent.parent.name == python_dir:
            dest_elements = [python_dir, 'lib-dynload', *dest_elements]

    return os.path.join(*dest_elements)


def process_collected_binary(
    src_name,
    dest_name,
    use_strip=False,
    use_upx=False,
    upx_exclude=None,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    strict_arch_validation=False
):
    """
    Process the collected binary using strip or UPX (or both), and apply any platform-specific processing. On macOS,
    this rewrites the library paths in the headers, and (re-)signs the binary. On-disk cache is used to avoid processing
    the same binary with same options over and over.

    In addition to given arguments, this function also uses CONF['cachedir'] and CONF['upx_dir'].
    """
    from PyInstaller.config import CONF

    # We need to use cache in the following scenarios:
    #  * extra binary processing due to use of `strip` or `upx`
    #  * building on macOS, where we need to rewrite library paths in binaries' headers and (re-)sign the binaries.
    if not use_strip and not use_upx and not is_darwin:
        return src_name

    # Match against provided UPX exclude patterns.
    upx_exclude = upx_exclude or []
    if use_upx:
        src_path = pathlib.PurePath(src_name)
        for upx_exclude_entry in upx_exclude:
            # pathlib.PurePath.match() matches from right to left, and supports * wildcard, but does not support the
            # "**" syntax for directory recursion. Case sensitivity follows the OS default.
            if src_path.match(upx_exclude_entry):
                logger.info("Disabling UPX for %s due to match in exclude pattern: %s", src_name, upx_exclude_entry)
                use_upx = False
                break

    # Additional automatic disablement rules for UPX and strip.

    # On Windows, avoid using UPX with binaries that have control flow guard (CFG) enabled.
    if use_upx and is_win and versioninfo.pefile_check_control_flow_guard(src_name):
        logger.info('Disabling UPX for %s due to CFG!', src_name)
        use_upx = False

    # Avoid using UPX with Qt plugins, as it strips the data required by the Qt plugin loader.
    if use_upx and misc.is_file_qt_plugin(src_name):
        logger.info('Disabling UPX for %s due to it being a Qt plugin!', src_name)
        use_upx = False

    # On linux, if a binary has an accompanying HMAC or CHK file, avoid modifying it in any way.
    if (use_upx or use_strip) and is_linux:
        src_path = pathlib.Path(src_name)
        hmac_path = src_path.with_name(f".{src_path.name}.hmac")
        chk_path = src_path.with_suffix(".chk")
        if hmac_path.is_file():
            logger.info('Disabling UPX and/or strip for %s due to accompanying .hmac file!', src_name)
            use_upx = use_strip = False
        elif chk_path.is_file():
            logger.info('Disabling UPX and/or strip for %s due to accompanying .chk file!', src_name)
            use_upx = use_strip = False
        del src_path, hmac_path, chk_path

    # Exit early if no processing is required after above rules are applied.
    if not use_strip and not use_upx and not is_darwin:
        return src_name

    # Prepare cache directory path. Cache is tied to python major/minor version, but also to various processing options.
    pyver = f'py{sys.version_info[0]}{sys.version_info[1]}'
    arch = platform.architecture()[0]
    cache_dir = os.path.join(
        CONF['cachedir'],
        f'bincache{use_strip:d}{use_upx:d}{pyver}{arch}',
    )
    if target_arch:
        cache_dir = os.path.join(cache_dir, target_arch)
    if is_darwin:
        # Separate by codesign identity
        if codesign_identity:
            # Compute hex digest of codesign identity string to prevent issues with invalid characters.
            csi_hash = hashlib.sha256(codesign_identity.encode('utf-8'))
            cache_dir = os.path.join(cache_dir, csi_hash.hexdigest())
        else:
            cache_dir = os.path.join(cache_dir, 'adhoc')  # ad-hoc signing
        # Separate by entitlements
        if entitlements_file:
            # Compute hex digest of entitlements file contents
            with open(entitlements_file, 'rb') as fp:
                ef_hash = hashlib.sha256(fp.read())
            cache_dir = os.path.join(cache_dir, ef_hash.hexdigest())
        else:
            cache_dir = os.path.join(cache_dir, 'no-entitlements')
    os.makedirs(cache_dir, exist_ok=True)

    # Load cache index, if available
    cache_index_file = os.path.join(cache_dir, "index.dat")
    try:
        cache_index = misc.load_py_data_struct(cache_index_file)
    except FileNotFoundError:
        cache_index = {}
    except Exception:
        # Tell the user they may want to fix their cache... However, do not delete it for them; if it keeps getting
        # corrupted, we will never find out.
        logger.warning("PyInstaller bincache may be corrupted; use pyinstaller --clean to fix it.")
        raise

    # Look up the file in cache; use case-normalized destination name as identifier.
    cached_id = os.path.normcase(dest_name)
    cached_name = os.path.join(cache_dir, dest_name)
    src_digest = _compute_file_digest(src_name)

    if cached_id in cache_index:
        # If digest matches to the cached digest, return the cached file...
        if src_digest == cache_index[cached_id]:
            return cached_name

        # ... otherwise remove it.
        os.remove(cached_name)

    # Ensure parent path exists
    os.makedirs(os.path.dirname(cached_name), exist_ok=True)

    # Use `shutil.copyfile` to copy the file with default permissions bits, then manually set executable
    # bits. This way, we avoid copying permission bits and metadata from the original file, which might be too
    # restrictive for further processing (read-only permissions, immutable flag on FreeBSD, and so on).
    shutil.copyfile(src_name, cached_name)
    os.chmod(cached_name, 0o755)

    # Apply strip
    if use_strip:
        strip_options = []
        if is_darwin:
            # The default strip behavior breaks some shared libraries under macOS.
            strip_options = ["-S"]  # -S = strip only debug symbols.
        elif is_aix:
            # Set -X32_64 flag to have strip transparently process both 32-bit and 64-bit binaries, without user having
            # to set OBJECT_MODE environment variable prior to the build. Also accommodates potential mixed-case
            # scenario, for example a 32-bit utility program being collected into a 64-bit application bundle.
            strip_options = ["-X32_64"]

        cmd = ["strip", *strip_options, cached_name]
        logger.info("Executing: %s", " ".join(cmd))
        try:
            p = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                errors='ignore',
                encoding='utf-8',
            )
            logger.debug("Output from strip command:\n%s", p.stdout)
        except subprocess.CalledProcessError as e:
            show_warning = True

            # On AIX, strip utility raises an error when ran against already-stripped binary. Catch the corresponding
            # message (`0654-419 The specified archive file was already stripped.`) and suppress the warning.
            if is_aix and "0654-419" in e.stdout:
                show_warning = False

            if show_warning:
                logger.warning("Failed to run strip on %r!", cached_name, exc_info=True)
                logger.warning("Output from strip command:\n%s", e.stdout)
        except Exception:
            logger.warning("Failed to run strip on %r!", cached_name, exc_info=True)

    # Apply UPX
    if use_upx:
        upx_exe = 'upx'
        upx_dir = CONF['upx_dir']
        if upx_dir:
            upx_exe = os.path.join(upx_dir, upx_exe)

        upx_options = [
            # Do not compress icons, so that they can still be accessed externally.
            '--compress-icons=0',
            # Use LZMA compression.
            '--lzma',
            # Quiet mode.
            '-q',
        ]
        if is_win:
            # Binaries built with Visual Studio 7.1 require --strip-loadconf or they will not compress.
            upx_options.append('--strip-loadconf')

        cmd = [upx_exe, *upx_options, cached_name]
        logger.info("Executing: %s", " ".join(cmd))
        try:
            p = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                errors='ignore',
                encoding='utf-8',
            )
            logger.debug("Output from upx command:\n%s", p.stdout)
        except subprocess.CalledProcessError as e:
            logger.warning("Failed to upx strip on %r!", cached_name, exc_info=True)
            logger.warning("Output from upx command:\n%s", e.stdout)
        except Exception:
            logger.warning("Failed to run upx on %r!", cached_name, exc_info=True)

    # On macOS, we need to modify the given binary's paths to the dependent libraries, in order to ensure they are
    # relocatable and always refer to location within the frozen application. Specifically, we make all dependent
    # library paths relative to @rpath, and set @rpath to point to the top-level application directory, relative to
    # the binary's location (i.e., @loader_path).
    #
    # While modifying the headers invalidates existing signatures, we avoid removing them in order to speed things up
    # (and to avoid potential bugs in the codesign utility, like the one reported on macOS 10.13 in #6167).
    # The forced re-signing at the end should take care of the invalidated signatures.
    if is_darwin:
        try:
            osxutils.binary_to_target_arch(cached_name, target_arch, display_name=src_name)
            #osxutils.remove_signature_from_binary(cached_name)  # Disabled as per comment above.
            target_rpath = str(
                pathlib.PurePath('@loader_path', *['..' for level in pathlib.PurePath(dest_name).parent.parts])
            )
            osxutils.set_dylib_dependency_paths(cached_name, target_rpath)
            osxutils.sign_binary(cached_name, codesign_identity, entitlements_file)
        except osxutils.InvalidBinaryError:
            # Raised by osxutils.binary_to_target_arch when the given file is not a valid macOS binary (for example,
            # a linux .so file; see issue #6327). The error prevents any further processing, so just ignore it.
            pass
        except osxutils.IncompatibleBinaryArchError:
            # Raised by osxutils.binary_to_target_arch when the given file does not contain (all) required arch slices.
            # Depending on the strict validation mode, re-raise or swallow the error.
            #
            # Strict validation should be enabled only for binaries where the architecture *must* match the target one,
            # i.e., the extension modules. Everything else is pretty much a gray area, for example:
            #  * a universal2 extension may have its x86_64 and arm64 slices linked against distinct single-arch/thin
            #    shared libraries
            #  * a collected executable that is launched by python code via a subprocess can be x86_64-only, even though
            #    the actual python code is running on M1 in native arm64 mode.
            if strict_arch_validation:
                raise
            logger.debug("File %s failed optional architecture validation - collecting as-is!", src_name)
        except Exception as e:
            raise SystemError(f"Failed to process binary {cached_name!r}!") from e

    # Update cache index
    cache_index[cached_id] = src_digest
    misc.save_py_data_struct(cache_index_file, cache_index)

    return cached_name


def _compute_file_digest(filename):
    hasher = hashlib.sha1()
    with open(filename, "rb") as fp:
        for chunk in iter(lambda: fp.read(16 * 1024), b""):
            hasher.update(chunk)
    return bytearray(hasher.digest())


def _check_path_overlap(path):
    """
    Check that path does not overlap with WORKPATH or SPECPATH (i.e., WORKPATH and SPECPATH may not start with path,
    which could be caused by a faulty hand-edited specfile).

    Raise SystemExit if there is overlap, return True otherwise
    """
    from PyInstaller.config import CONF
    specerr = 0
    if CONF['workpath'].startswith(path):
        logger.error('Specfile error: The output path "%s" contains WORKPATH (%s)', path, CONF['workpath'])
        specerr += 1
    if CONF['specpath'].startswith(path):
        logger.error('Specfile error: The output path "%s" contains SPECPATH (%s)', path, CONF['specpath'])
        specerr += 1
    if specerr:
        raise SystemExit(
            'ERROR: Please edit/recreate the specfile (%s) and set a different output name (e.g. "dist").' %
            CONF['spec']
        )
    return True


def _make_clean_directory(path):
    """
    Create a clean directory from the given directory name.
    """
    if _check_path_overlap(path):
        if os.path.isdir(path) or os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                _rmtree(path)

        os.makedirs(path, exist_ok=True)


def _rmtree(path):
    """
    Remove directory and all its contents, but only after user confirmation, or if the -y option is set.
    """
    from PyInstaller.config import CONF
    if CONF['noconfirm']:
        choice = 'y'
    elif sys.stdout.isatty():
        choice = input(
            'WARNING: The output directory "%s" and ALL ITS CONTENTS will be REMOVED! Continue? (y/N)' % path
        )
    else:
        raise SystemExit(
            'ERROR: The output directory "%s" is not empty. Please remove all its contents or use the -y option (remove'
            ' output directory without confirmation).' % path
        )
    if choice.strip().lower() == 'y':
        if not CONF['noconfirm']:
            print("On your own risk, you can use the option `--noconfirm` to get rid of this question.")
        logger.info('Removing dir %s', path)
        shutil.rmtree(path)
    else:
        raise SystemExit('User aborted')


# TODO Refactor to prohibit empty target directories. As the docstring below documents, this function currently permits
# the second item of each 2-tuple in "hook.datas" to be the empty string, in which case the target directory defaults to
# the source directory's basename. However, this functionality is very fragile and hence bad. Instead:
#
# * An exception should be raised if such item is empty.
# * All hooks currently passing the empty string for such item (e.g.,
#   "hooks/hook-babel.py", "hooks/hook-matplotlib.py") should be refactored
#   to instead pass such basename.
def format_binaries_and_datas(binaries_or_datas, workingdir=None):
    """
    Convert the passed list of hook-style 2-tuples into a returned set of `TOC`-style 2-tuples.

    Elements of the passed list are 2-tuples `(source_dir_or_glob, target_dir)`.
    Elements of the returned set are 2-tuples `(target_file, source_file)`.
    For backwards compatibility, the order of elements in the former tuples are the reverse of the order of elements in
    the latter tuples!

    Parameters
    ----------
    binaries_or_datas : list
        List of hook-style 2-tuples (e.g., the top-level `binaries` and `datas` attributes defined by hooks) whose:
        * The first element is either:
          * A glob matching only the absolute or relative paths of source non-Python data files.
          * The absolute or relative path of a source directory containing only source non-Python data files.
        * The second element is the relative path of the target directory into which these source files will be
          recursively copied.

        If the optional `workingdir` parameter is passed, source paths may be either absolute or relative; else, source
        paths _must_ be absolute.
    workingdir : str
        Optional absolute path of the directory to which all relative source paths in the `binaries_or_datas`
        parameter will be prepended by (and hence converted into absolute paths) _or_ `None` if these paths are to be
        preserved as relative. Defaults to `None`.

    Returns
    ----------
    set
        Set of `TOC`-style 2-tuples whose:
        * First element is the absolute or relative path of a target file.
        * Second element is the absolute or relative path of the corresponding source file to be copied to this target
          file.
    """
    toc_datas = set()

    for src_root_path_or_glob, trg_root_dir in binaries_or_datas:
        # Disallow empty source path. Those are typically result of errors, and result in implicit collection of the
        # whole current working directory, which is never a good idea.
        if not src_root_path_or_glob:
            raise InvalidSrcDestTupleError(
                (src_root_path_or_glob, trg_root_dir),
                "Empty SRC is not allowed when adding binary and data files, as it would result in collection of the "
                "whole current working directory."
            )
        if not trg_root_dir:
            raise InvalidSrcDestTupleError(
                (src_root_path_or_glob, trg_root_dir),
                "Empty DEST_DIR is not allowed - to collect files into application's top-level directory, use "
                f"{os.curdir!r}."
            )
        # Disallow absolute target paths, as well as target paths that would end up pointing outside of the
        # application's top-level directory.
        if os.path.isabs(trg_root_dir):
            raise InvalidSrcDestTupleError((src_root_path_or_glob, trg_root_dir), "DEST_DIR must be a relative path!")
        if os.path.normpath(trg_root_dir).startswith('..'):
            raise InvalidSrcDestTupleError(
                (src_root_path_or_glob, trg_root_dir),
                "DEST_DIR must not point outside of application's top-level directory!",
            )

        # Convert relative to absolute paths if required.
        if workingdir and not os.path.isabs(src_root_path_or_glob):
            src_root_path_or_glob = os.path.join(workingdir, src_root_path_or_glob)

        # Normalize paths.
        src_root_path_or_glob = os.path.normpath(src_root_path_or_glob)

        # If given source path is a file or directory path, pass it on.
        # If not, treat it as a glob and pass on all matching paths. However, we need to preserve the directories
        # captured by the glob - as opposed to collecting their contents into top-level target directory. Therefore,
        # we set a flag which is used in subsequent processing to distinguish between original directory paths and
        # directory paths that were captured by the glob.
        if os.path.isfile(src_root_path_or_glob) or os.path.isdir(src_root_path_or_glob):
            src_root_paths = [src_root_path_or_glob]
            was_glob = False
        else:
            src_root_paths = glob.glob(src_root_path_or_glob)
            was_glob = True

        if not src_root_paths:
            raise SystemExit(f'ERROR: Unable to find {src_root_path_or_glob!r} when adding binary and data files.')

        for src_root_path in src_root_paths:
            if os.path.isfile(src_root_path):
                # Normalizing the result to remove redundant relative paths (e.g., removing "./" from "trg/./file").
                toc_datas.add((
                    os.path.normpath(os.path.join(trg_root_dir, os.path.basename(src_root_path))),
                    os.path.normpath(src_root_path),
                ))
            elif os.path.isdir(src_root_path):
                for src_dir, src_subdir_basenames, src_file_basenames in os.walk(src_root_path):
                    # Ensure the current source directory is a subdirectory of the passed top-level source directory.
                    # Since os.walk() does *NOT* follow symlinks by default, this should be the case. (But let's make
                    # sure.)
                    assert src_dir.startswith(src_root_path)

                    # Relative path of the current target directory, obtained by:
                    #
                    # * Stripping the top-level source directory from the current source directory (e.g., removing
                    #   "/top" from "/top/dir").
                    # * Normalizing the result to remove redundant relative paths (e.g., removing "./" from
                    #   "trg/./file").
                    if was_glob:
                        # Preserve directories captured by glob.
                        rel_dir = os.path.relpath(src_dir, os.path.dirname(src_root_path))
                    else:
                        rel_dir = os.path.relpath(src_dir, src_root_path)
                    trg_dir = os.path.normpath(os.path.join(trg_root_dir, rel_dir))

                    for src_file_basename in src_file_basenames:
                        src_file = os.path.join(src_dir, src_file_basename)
                        if os.path.isfile(src_file):
                            # Normalize the result to remove redundant relative paths (e.g., removing "./" from
                            # "trg/./file").
                            toc_datas.add((
                                os.path.normpath(os.path.join(trg_dir, src_file_basename)), os.path.normpath(src_file)
                            ))

    return toc_datas


def get_code_object(modname, filename, optimize):
    """
    Get the code-object for a module.

    This is a simplifed non-performant version which circumvents __pycache__.
    """

    # Once upon a time, we compiled dummy code objects for PEP-420 namespace packages. We do not do that anymore.
    assert filename not in {'-', None}, "Called with PEP-420 namespace package!"

    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == '.pyc':
        # The module is available in binary-only form. Read the contents of .pyc file using helper function, which
        # supports reading from either stand-alone or archive-embedded .pyc files.
        logger.debug('Reading code object from .pyc file %s', filename)
        pyc_data = _read_pyc_data(filename)
        code_object = marshal.loads(pyc_data[16:])
    else:
        # Assume this is a source .py file, but allow an arbitrary extension (other than .pyc, which is taken in
        # the above branch). This allows entry-point scripts to have an arbitrary (or no) extension, as tested by
        # the `test_arbitrary_ext` in `test_basic.py`.
        logger.debug('Compiling python script/module file %s', filename)

        with open(filename, 'rb') as f:
            source = f.read()

        # If entry-point script has no suffix, append .py when compiling the source. In POSIX builds, the executable
        # has no suffix either; this causes issues with `traceback` module, as it tries to read the executable file
        # when trying to look up the code for the entry-point script (when current working directory contains the
        # executable).
        _, ext = os.path.splitext(filename)
        if not ext:
            logger.debug("Appending .py to compiled entry-point name...")
            filename += '.py'

        try:
            code_object = compile(source, filename, 'exec', optimize=optimize)
        except SyntaxError:
            logger.warning("Sytnax error while compiling %s", filename)
            raise

    return code_object


def replace_filename_in_code_object(code_object, filename):
    """
    Recursively replace the `co_filename` in the given code object and code objects stored in its `co_consts` entries.
    Primarily used to anonymize collected code objects, i.e., by removing the build environment's paths from them.
    """

    consts = tuple(
        replace_filename_in_code_object(const_co, filename) if isinstance(const_co, types.CodeType) else const_co
        for const_co in code_object.co_consts
    )

    return code_object.replace(co_consts=consts, co_filename=filename)


def _should_include_system_binary(binary_tuple, exceptions):
    """
    Return True if the given binary_tuple describes a system binary that should be included.

    Exclude all system library binaries other than those with "lib-dynload" in the destination or "python" in the
    source, except for those matching the patterns in the exceptions list. Intended to be used from the Analysis
    exclude_system_libraries method.
    """
    dest = binary_tuple[0]
    if dest.startswith(f'python{sys.version_info.major}.{sys.version_info.minor}/lib-dynload'):
        return True
    src = binary_tuple[1]
    if fnmatch.fnmatch(src, '*python*'):
        return True
    if not src.startswith('/lib') and not src.startswith('/usr/lib'):
        return True
    for exception in exceptions:
        if fnmatch.fnmatch(dest, exception):
            return True
    return False


def compile_pymodule(name, src_path, workpath, optimize, code_cache=None):
    """
    Given the name and source file for a pure-python module, compile the module in the specified working directory,
    and return the name of resulting .pyc file. The paths in the resulting .pyc module are anonymized by having their
    absolute prefix removed.

    If a .pyc file with matching name already exists in the target working directory, it is re-used (provided it has
    compatible bytecode magic in the header, and that its modification time is newer than that of the source file).

    If the specified module is available in binary-only form, the input .pyc file is copied to the target working
    directory and post-processed. If the specified module is available in source form, it is compiled only if
    corresponding code object is not available in the optional code-object cache; otherwise, it is copied from cache
    and post-processed. When compiling the module, the specified byte-code optimization level is used.

    It is up to caller to ensure that the optional code-object cache contains only code-objects of target optimization
    level, and that if the specified working directory already contains .pyc files, that they were created with target
    optimization level.
    """

    # Construct the target .pyc filename in the workpath
    split_name = name.split(".")
    if "__init__" in src_path:
        # __init__ module; use "__init__" as module name, and construct parent path using all components of the
        # fully-qualified name
        parent_dirs = split_name
        mod_basename = "__init__"
    else:
        # Regular module; use last component of the fully-qualified name as module name, and the rest as the parent
        # path.
        parent_dirs = split_name[:-1]
        mod_basename = split_name[-1]
    pyc_path = os.path.join(workpath, *parent_dirs, mod_basename + '.pyc')

    # Check if optional cache contains module entry
    code_object = code_cache.get(name, None) if code_cache else None

    if code_object is None:
        _, ext = os.path.splitext(src_path)
        ext = ext.lower()

        if ext == '.py':
            # Source py file; read source and compile it.
            with open(src_path, 'rb') as f:
                src_data = f.read()
            code_object = compile(src_data, src_path, 'exec', optimize=optimize)
        elif ext == '.pyc':
            # The module is available in binary-only form. Read the contents of .pyc file using helper function, which
            # supports reading from either stand-alone or archive-embedded .pyc files.
            pyc_data = _read_pyc_data(src_path)
            # Unmarshal code object; this is necessary if we want to strip paths from it
            code_object = marshal.loads(pyc_data[16:])
        else:
            raise ValueError(f"Invalid python module file {src_path}; unhandled extension {ext}!")

    # Replace co_filename in code object with anonymized filename that does not contain full path. Construct the
    # relative filename from module name, similar how we earlier constructed the `pyc_path`.
    co_filename = os.path.join(*parent_dirs, mod_basename + '.py')
    code_object = replace_filename_in_code_object(code_object, co_filename)

    # Write complete .pyc module to in-memory stream. Then, check if .pyc file already exists, compare contents, and
    # (re)write it only if different. This avoids unnecessary (re)writing of the file, and in turn also avoids
    # unnecessary cache invalidation for targets that make use of the .pyc file (e.g., PKG, COLLECT).
    with io.BytesIO() as pyc_stream:
        pyc_stream.write(compat.BYTECODE_MAGIC)
        pyc_stream.write(struct.pack('<I', 0b01))  # PEP-552: hash-based pyc, check_source=False
        pyc_stream.write(b'\00' * 8)  # Zero the source hash
        marshal.dump(code_object, pyc_stream)
        pyc_data = pyc_stream.getvalue()

    if os.path.isfile(pyc_path):
        with open(pyc_path, 'rb') as fh:
            existing_pyc_data = fh.read()
        if pyc_data == existing_pyc_data:
            return pyc_path  # Return path to (existing) file.

    # Ensure the existence of parent directories for the target pyc path
    os.makedirs(os.path.dirname(pyc_path), exist_ok=True)

    # Write
    with open(pyc_path, 'wb') as fh:
        fh.write(pyc_data)

    # Return output path
    return pyc_path


def _read_pyc_data(filename):
    """
    Helper for reading data from .pyc files. Supports both stand-alone and archive-embedded .pyc files. Used by
    `compile_pymodule` and `get_code_object` helper functions.
    """
    src_file = pathlib.Path(filename)

    if src_file.is_file():
        # Stand-alone .pyc file.
        pyc_data = src_file.read_bytes()
    else:
        # Check if .pyc file is stored in a .zip archive, as is the case for stdlib modules in embeddable
        # python on Windows.
        parent_zip_file = misc.path_to_parent_archive(src_file)
        if parent_zip_file is not None and zipfile.is_zipfile(parent_zip_file):
            with zipfile.ZipFile(parent_zip_file, 'r') as zip_archive:
                # NOTE: zip entry names must be in POSIX format, even on Windows!
                zip_entry_name = str(src_file.relative_to(parent_zip_file).as_posix())
                pyc_data = zip_archive.read(zip_entry_name)
        else:
            raise FileNotFoundError(f"Cannot find .pyc file {filename!r}!")

        # Verify the python version
        if pyc_data[:4] != compat.BYTECODE_MAGIC:
            raise ValueError(f"The .pyc module {filename} was compiled for incompatible version of python!")

    return pyc_data


def postprocess_binaries_toc_pywin32(binaries):
    """
    Process the given `binaries` TOC list to apply work around for `pywin32` package, fixing the target directory
    for collected extensions.
    """
    # Ensure that all files collected from `win32`  or `pythonwin` into top-level directory are put back into
    # their corresponding directories. They end up in top-level directory because `pywin32.pth` adds both
    # directories to the `sys.path`, so they end up visible as top-level directories. But these extensions
    # might in fact be linked against each other, so we should preserve the directory layout for consistency
    # between modulegraph-discovered extensions and linked binaries discovered by link-time dependency analysis.
    # Within the same framework, also consider `pywin32_system32`, just in case.
    PYWIN32_SUBDIRS = {'win32', 'pythonwin', 'pywin32_system32'}

    processed_binaries = []
    for dest_name, src_name, typecode in binaries:
        dest_path = pathlib.PurePath(dest_name)
        src_path = pathlib.PurePath(src_name)

        if dest_path.parent == pathlib.PurePath('.') and src_path.parent.name.lower() in PYWIN32_SUBDIRS:
            dest_path = pathlib.PurePath(src_path.parent.name) / dest_path
            dest_name = str(dest_path)

        processed_binaries.append((dest_name, src_name, typecode))

    return processed_binaries


def postprocess_binaries_toc_pywin32_anaconda(binaries):
    """
    Process the given `binaries` TOC list to apply work around for Anaconda `pywin32` package, fixing the location
    of collected `pywintypes3X.dll` and `pythoncom3X.dll`.
    """
    # The Anaconda-provided `pywin32` package installs three copies of `pywintypes3X.dll` and `pythoncom3X.dll`,
    # located in the following directories (relative to the environment):
    # - Library/bin
    # - Lib/site-packages/pywin32_system32
    # - Lib/site-packages/win32
    #
    # This turns our dependency scanner and directory layout preservation mechanism into a lottery based on what
    # `pywin32` modules are imported and in what order. To keep things simple, we deal with this insanity by
    # post-processing the `binaries` list, modifying the destination of offending copies, and let the final TOC
    # list normalization deal with potential duplicates.
    DLL_CANDIDATES = {
        f"pywintypes{sys.version_info[0]}{sys.version_info[1]}.dll",
        f"pythoncom{sys.version_info[0]}{sys.version_info[1]}.dll",
    }

    DUPLICATE_DIRS = {
        pathlib.PurePath('.'),
        pathlib.PurePath('win32'),
    }

    processed_binaries = []
    for dest_name, src_name, typecode in binaries:
        # Check if we need to divert - based on the destination base name and destination parent directory.
        dest_path = pathlib.PurePath(dest_name)
        if dest_path.name.lower() in DLL_CANDIDATES and dest_path.parent in DUPLICATE_DIRS:
            dest_path = pathlib.PurePath("pywin32_system32") / dest_path.name
            dest_name = str(dest_path)

        processed_binaries.append((dest_name, src_name, typecode))

    return processed_binaries


def create_base_library_zip(filename, modules_toc, code_cache=None):
    """
    Create a zip archive with python modules that are needed during python interpreter initialization.
    """
    with zipfile.ZipFile(filename, 'w') as zf:
        for name, src_path, typecode in modules_toc:
            # Obtain code object from cache, or compile it.
            code = None if code_cache is None else code_cache.get(name, None)
            if code is None:
                optim_level = {'PYMODULE': 0, 'PYMODULE-1': 1, 'PYMODULE-2': 2}[typecode]
                code = get_code_object(name, src_path, optimize=optim_level)
            # Determine destination name
            dest_name = name.replace('.', os.sep)
            # Special case: packages have an implied `__init__` filename that needs to be added.
            basename, ext = os.path.splitext(os.path.basename(src_path))
            if basename == '__init__':
                dest_name += os.sep + '__init__'
            dest_name += '.pyc'  # Always .pyc, regardless of optimization level.
            # Replace full-path co_filename in code object with `dest_name` (and shorten suffix from .pyc to .py).
            code = replace_filename_in_code_object(code, dest_name[:-1])
            # Write the .pyc module
            with io.BytesIO() as fc:
                fc.write(compat.BYTECODE_MAGIC)
                fc.write(struct.pack('<I', 0b01))  # PEP-552: hash-based pyc, check_source=False
                fc.write(b'\00' * 8)  # Match behavior of `building.utils.compile_pymodule`
                marshal.dump(code, fc)
                # Use a ZipInfo to set timestamp for deterministic build.
                info = zipfile.ZipInfo(dest_name)
                zf.writestr(info, fc.getvalue())
