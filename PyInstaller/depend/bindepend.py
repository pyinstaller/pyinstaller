#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
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
import functools
import os
import pathlib
import re
import sys
import sysconfig
import subprocess

from PyInstaller import compat
from PyInstaller import log as logging
from PyInstaller.depend import dylib, utils
from PyInstaller.utils.win32 import winutils
from PyInstaller.exceptions import PythonLibraryNotFoundError

if compat.is_darwin:
    import PyInstaller.utils.osx as osxutils

logger = logging.getLogger(__name__)

_exe_machine_type = None
if compat.is_win:
    _exe_machine_type = winutils.get_pe_file_machine_type(compat.python_executable)

#- High-level binary dependency analysis


def _get_paths_for_parent_directory_preservation():
    """
    Return list of paths that serve as prefixes for parent-directory preservation of collected binaries and/or
    shared libraries. If a binary is collected from a location that starts with a path from this list, the relative
    directory structure is preserved within the frozen application bundle; otherwise, the binary is collected to the
    frozen application's top-level directory.
    """

    # Use only site-packages paths. We have no control over contents of `sys.path`, so using all paths from that may
    # lead to unintended behavior in corner cases. For example, if `sys.path` contained the drive root (see #7028),
    # all paths that do not match some other sub-path rooted in that drive will end up recognized as relative to the
    # drive root. In such case, any DLL collected from `c:\Windows\system32` will be collected into `Windows\system32`
    # sub-directory; ucrt DLLs collected from MSVC or Windows SDK installed in `c:\Program Files\...` will end up
    # collected into `Program Files\...` subdirectory; etc.
    #
    # On the other hand, the DLL parent directory preservation is primarily aimed at packages installed via PyPI
    # wheels, which are typically installed into site-packages. Therefore, limiting the directory preservation for
    # shared libraries collected from site-packages should do the trick, and should be reasonably safe.
    import site

    orig_paths = site.getsitepackages()
    orig_paths.append(site.getusersitepackages())

    # Explicitly excluded paths. `site.getsitepackages` seems to include `sys.prefix`, which we need to exclude, to
    # avoid issue swith DLLs in its sub-directories. We need both resolved and unresolved variant to handle cases
    # where `base_prefix` itself is a symbolic link (e.g., `scoop`-installed python on Windows, see #8023).
    excluded_paths = {
        pathlib.Path(sys.base_prefix),
        pathlib.Path(sys.base_prefix).resolve(),
        pathlib.Path(sys.prefix),
        pathlib.Path(sys.prefix).resolve(),
    }

    # For each path in orig_paths, append a resolved variant. This helps with linux venv where we need to consider
    # both `venv/lib/python3.11/site-packages` and `venv/lib/python3.11/site-packages` and `lib64` is a symlink
    # to `lib`.
    orig_paths += [pathlib.Path(path).resolve() for path in orig_paths]

    paths = set()
    for path in orig_paths:
        if not path:
            continue
        path = pathlib.Path(path)
        # Filter out non-directories (e.g., /path/to/python3x.zip) or non-existent paths
        if not path.is_dir():
            continue
        # Filter out explicitly excluded paths
        if path in excluded_paths:
            continue
        paths.add(path)

    # Sort by length (in term of path components) to ensure match against the longest common prefix (for example, match
    # /path/to/venv/lib/site-packages instead of /path/to/venv when both paths are in site paths).
    paths = sorted(paths, key=lambda x: len(x.parents), reverse=True)

    return paths


def _select_destination_directory(src_filename, parent_dir_preservation_paths):
    # Check parent directory preservation paths
    for parent_dir_preservation_path in parent_dir_preservation_paths:
        if parent_dir_preservation_path in src_filename.parents:
            # Collect into corresponding sub-directory.
            return src_filename.relative_to(parent_dir_preservation_path)

    # Collect into top-level directory.
    return src_filename.name


def binary_dependency_analysis(binaries, search_paths=None, symlink_suppression_patterns=None):
    """
    Perform binary dependency analysis on the given TOC list of collected binaries, by recursively scanning each binary
    for linked dependencies (shared library imports). Returns new TOC list that contains both original entries and their
    binary dependencies.

    Additional search paths for dependencies' full path resolution may be supplied via optional argument.
    """

    # Get all path prefixes for binaries' parent-directory preservation. For binaries collected from packages in (for
    # example) site-packages directory, we should try to preserve the parent directory structure.
    parent_dir_preservation_paths = _get_paths_for_parent_directory_preservation()

    # Keep track of processed binaries and processed dependencies.
    processed_binaries = set()
    processed_dependencies = set()

    # Keep track of unresolved dependencies, in order to defer the missing-library warnings until after everything has
    # been processed. This allows us to suppress warnings for dependencies that end up being collected anyway; for
    # details, see the end of this function.
    missing_dependencies = []

    # Populate output TOC with input binaries - this also serves as TODO list, as we iterate over it while appending
    # new entries at the end.
    output_toc = binaries[:]
    for dest_name, src_name, typecode in output_toc:
        # Do not process symbolic links (already present in input TOC list, or added during analysis below).
        if typecode == 'SYMLINK':
            continue

        # Keep track of processed binaries, to avoid unnecessarily repeating analysis of the same file. Use pathlib.Path
        # to avoid having to worry about case normalization.
        src_path = pathlib.Path(src_name)
        if src_path in processed_binaries:
            continue
        processed_binaries.add(src_path)

        logger.debug("Analyzing binary %r", src_name)

        # Analyze imports (linked dependencies)
        for dep_name, dep_src_path in get_imports(src_name, search_paths):
            logger.debug("Processing dependency, name: %r, resolved path: %r", dep_name, dep_src_path)

            # Skip unresolved dependencies. Defer the missing-library warnings until after binary dependency analysis
            # is complete.
            if not dep_src_path:
                missing_dependencies.append((dep_name, src_name))
                continue

            # Compare resolved dependency against global inclusion/exclusion rules.
            if not dylib.include_library(dep_src_path):
                logger.debug("Skipping dependency %r due to global exclusion rules.", dep_src_path)
                continue

            dep_src_path = pathlib.Path(dep_src_path)  # Turn into pathlib.Path for subsequent processing

            # Avoid processing this dependency if we have already processed it.
            if dep_src_path in processed_dependencies:
                logger.debug("Skipping dependency %r due to prior processing.", str(dep_src_path))
                continue
            processed_dependencies.add(dep_src_path)

            # Try to preserve parent directory structure, if applicable.
            # NOTE: do not resolve the source path, because on macOS and linux, it may be a versioned .so (e.g.,
            # libsomething.so.1, pointing at libsomething.so.1.2.3), and we need to collect it under original name!
            dep_dest_path = _select_destination_directory(dep_src_path, parent_dir_preservation_paths)
            dep_dest_path = pathlib.PurePath(dep_dest_path)  # Might be a str() if it is just a basename...

            # If we are collecting library into top-level directory on macOS, check whether it comes from a
            # .framework bundle. If it does, re-create the .framework bundle in the top-level directory
            # instead.
            if compat.is_darwin and dep_dest_path.parent == pathlib.PurePath('.'):
                if osxutils.is_framework_bundle_lib(dep_src_path):
                    # dst_src_path is parent_path/Name.framework/Versions/Current/Name
                    framework_parent_path = dep_src_path.parent.parent.parent.parent
                    dep_dest_path = pathlib.PurePath(dep_src_path.relative_to(framework_parent_path))

            logger.debug("Collecting dependency %r as %r.", str(dep_src_path), str(dep_dest_path))
            output_toc.append((str(dep_dest_path), str(dep_src_path), 'BINARY'))

            # On non-Windows, if we are not collecting the binary into application's top-level directory ('.'),
            # add a symbolic link from top-level directory to the actual location. This is to accommodate
            # LD_LIBRARY_PATH being set to the top-level application directory on linux (although library search
            # should be mostly done via rpaths, so this might be redundant) and to accommodate library path
            # rewriting on macOS, which assumes that the library was collected into top-level directory.
            if compat.is_win:
                # We do not use symlinks on Windows.
                pass
            elif dep_dest_path.parent == pathlib.PurePath('.'):
                # The shared library itself is being collected into top-level application directory.
                pass
            elif any(dep_src_path.match(pattern) for pattern in symlink_suppression_patterns):
                # Honor symlink suppression patterns specified by hooks.
                logger.debug(
                    "Skipping symbolic link from %r to top-level application directory due to source path matching one "
                    "of symlink suppression path patterns.", str(dep_dest_path)
                )
            else:
                logger.debug("Adding symbolic link from %r to top-level application directory.", str(dep_dest_path))
                output_toc.append((str(dep_dest_path.name), str(dep_dest_path), 'SYMLINK'))

    # Handle missing dependencies: display warnings, add missing symbolic links to top-level application directory, etc.
    seen_binaries = {
        os.path.normcase(os.path.basename(src_name)): (dest_name, src_name, typecode)
        for dest_name, src_name, typecode in output_toc if typecode != 'SYMLINK'
    }
    existing_symlinks = set([dest_name for dest_name, src_name, typecode in output_toc if typecode == 'SYMLINK'])

    for dependency_name, referring_binary in missing_dependencies:
        # Ignore libraries that we would not collect in the first place.
        if not dylib.include_library(dependency_name):
            continue

        # If the binary with a matching basename happens to be among the discovered binaries, suppress the message as
        # well. This might happen either because the library was collected by some other mechanism (for example, via
        # hook, or supplied by the user), or because it was discovered during the analysis of another binary (which,
        # for example, had properly set run-paths on Linux/macOS or was located next to that other analyzed binary on
        # Windows).
        #
        # On non-Windows, also check if symbolic link to the discovered binary already exists in the top-level
        # application directory, and if not, create it. This is important especially on macOS, where our library path
        # rewriting assumes that all dependent libraries are available in the top-level application directory, or
        # linked into it.
        dependency_basename = os.path.normcase(os.path.basename(dependency_name))
        dependency_toc_entry = seen_binaries.get(dependency_basename, None)
        if dependency_toc_entry is None:
            # Not found, emit a warning (subject to global warning suppression rules).
            if not dylib.warn_missing_lib(dependency_name):
                continue
            logger.warning(
                "Library not found: could not resolve %r, dependency of %r.", dependency_name, referring_binary
            )
        elif not compat.is_win:
            # Found; generate symbolic link if necessary.
            dependency_dest_path = pathlib.PurePath(dependency_toc_entry[0])
            dependency_src_path = pathlib.Path(dependency_toc_entry[1])

            if dependency_dest_path.parent == pathlib.PurePath('.'):
                # The binary is collected into top-level application directory.
                continue
            elif dependency_basename in existing_symlinks:
                # The symbolic link already exists.
                continue

            # Keep honoring symlink suppression patterns specified by hooks (same as in main binary dependency analysis
            # loop).
            if any(dependency_src_path.match(pattern) for pattern in symlink_suppression_patterns):
                logger.info(
                    "Missing dependency handling: skipping symbolic link from %r to top-level application directory "
                    "due to source path matching one of symlink suppression path patterns.", str(dependency_dest_path)
                )
                continue

            # Create the symbolic link
            logger.info(
                "Missing dependency handling: adding symbolic link from %r to top-level application directory.",
                str(dependency_dest_path)
            )
            output_toc.append((dependency_basename, str(dependency_dest_path), 'SYMLINK'))
            existing_symlinks.add(dependency_basename)

    return output_toc


#- Low-level import analysis


def get_imports(filename, search_paths=None):
    """
    Analyze the given binary file (shared library or executable), and obtain the list of shared libraries it imports
    (i.e., link-time dependencies).

    Returns set of tuples (name, fullpath). The name component is the referenced name, and on macOS, may not be just
    a base name. If the library's full path cannot be resolved, fullpath element is None.

    Additional list of search paths may be specified via `search_paths`, to be used as a fall-back when the
    platform-specific resolution mechanism fails to resolve a library fullpath.
    """
    if compat.is_win:
        if str(filename).lower().endswith(".manifest"):
            return []
        return _get_imports_pefile(filename, search_paths)
    elif compat.is_darwin:
        return _get_imports_macholib(filename, search_paths)
    else:
        return _get_imports_ldd(filename, search_paths)


def _get_imports_pefile(filename, search_paths):
    """
    Windows-specific helper for `get_imports`, which uses the `pefile` library to walk through PE header.
    """
    import pefile

    output = set()

    # By default, pefile library parses all PE information. We are only interested in the list of dependent dlls.
    # Performance is improved by reading only needed information. https://code.google.com/p/pefile/wiki/UsageExamples
    pe = pefile.PE(filename, fast_load=True)
    pe.parse_data_directories(
        directories=[
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
        ],
        forwarded_exports_only=True,
        import_dllnames_only=True,
    )

    # If a library has no binary dependencies, pe.DIRECTORY_ENTRY_IMPORT does not exist.
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
        dll_str = entry.dll.decode('utf-8')
        output.add(dll_str)

    # We must also read the exports table to find forwarded symbols:
    # http://blogs.msdn.com/b/oldnewthing/archive/2006/07/19/671238.aspx
    exported_symbols = getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None)
    if exported_symbols:
        for symbol in exported_symbols.symbols:
            if symbol.forwarder is not None:
                # symbol.forwarder is a bytes object. Convert it to a string.
                forwarder = symbol.forwarder.decode('utf-8')
                # symbol.forwarder is for example 'KERNEL32.EnterCriticalSection'
                dll = forwarder.split('.')[0]
                output.add(dll + ".dll")

    pe.close()

    # Attempt to resolve full paths to referenced DLLs. Always add the input binary's parent directory to the search
    # paths.
    search_paths = [os.path.dirname(filename)] + (search_paths or [])
    output = {(lib, resolve_library_path(lib, search_paths)) for lib in output}

    return output


def _get_imports_ldd(filename, search_paths):
    """
    Helper for `get_imports`, which uses `ldd` to analyze shared libraries. Used on Linux and other POSIX-like platforms
    (with exception of macOS).
    """

    output = set()

    # Output of ldd varies between platforms...
    if compat.is_aix:
        # Match libs of the form
        #   'archivelib.a(objectmember.so/.o)'
        # or
        #   'sharedlib.so'
        # Will not match the fake lib '/unix'
        LDD_PATTERN = re.compile(r"^\s*(((?P<libarchive>(.*\.a))(?P<objectmember>\(.*\)))|((?P<libshared>(.*\.so))))$")
    elif compat.is_hpux:
        # Match libs of the form
        #   'sharedlib.so => full-path-to-lib
        # e.g.
        #   'libpython2.7.so =>      /usr/local/lib/hpux32/libpython2.7.so'
        LDD_PATTERN = re.compile(r"^\s+(.*)\s+=>\s+(.*)$")
    elif compat.is_solar:
        # Match libs of the form
        #   'sharedlib.so => full-path-to-lib
        # e.g.
        #   'libpython2.7.so.1.0 => /usr/local/lib/libpython2.7.so.1.0'
        # Will not match the platform specific libs starting with '/platform'
        LDD_PATTERN = re.compile(r"^\s+(.*)\s+=>\s+(.*)$")
    elif compat.is_linux:
        # Match libs of the form
        #   libpython3.13.so.1.0 => /home/brenainn/.pyenv/versions/3.13.0/lib/libpython3.13.so.1.0 (0x00007a9e15800000)
        # or
        #   /tmp/python/install/bin/../lib/libpython3.13.so.1.0 (0x00007b9489c82000)
        LDD_PATTERN = re.compile(r"^\s*(?:(.*?)\s+=>\s+)?(.*?)\s+\(.*\)")
    else:
        LDD_PATTERN = re.compile(r"\s*(.*?)\s+=>\s+(.*?)\s+\(.*\)")

    # Resolve symlinks since GNU ldd contains a bug in processing a symlink to a binary
    # using $ORIGIN: https://sourceware.org/bugzilla/show_bug.cgi?id=25263
    p = subprocess.run(
        ['ldd', os.path.realpath(filename)],
        stdin=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        encoding='utf-8',
    )

    ldd_warnings = []
    for line in p.stderr.splitlines():
        if not line:
            continue
        # Python extensions (including stdlib ones) are not linked against python.so but rely on Python's symbols having
        # already been loaded into symbol space at runtime. musl's ldd issues a series of harmless warnings to stderr
        # telling us that those symbols are unfindable. These should be suppressed.
        elif line.startswith("Error relocating ") and line.endswith(" symbol not found"):
            continue
        # Shared libraries should have the executable bits set; however, this is not the case for shared libraries
        # shipped in PyPI wheels, which cause ldd to emit `ldd: warning: you do not have execution permission for ...`
        # warnings. Suppress these.
        elif line.startswith("ldd: warning: you do not have execution permission for "):
            continue
        # When `ldd` is ran against a file that is not a dynamic binary (i.e., is not a binary at all, or is a static
        # binary), it emits a "not a dynamic executable" warning. Suppress it.
        elif "not a dynamic executable" in line:
            continue
        # Propagate any other warnings it might have.
        ldd_warnings.append(line)
    if ldd_warnings:
        logger.warning("ldd warnings for %r:\n%s", filename, "\n".join(ldd_warnings))

    for line in p.stdout.splitlines():
        name = None  # Referenced name
        lib = None  # Resolved library path

        m = LDD_PATTERN.search(line)
        if m:
            if compat.is_aix:
                libarchive = m.group('libarchive')
                if libarchive:
                    # We matched an archive lib with a request for a particular embedded shared object.
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
                name = name or os.path.basename(lib)
                if compat.is_linux:
                    # Skip all ld variants listed https://sourceware.org/glibc/wiki/ABIList
                    # plus musl's ld-musl-*.so.*.
                    if re.fullmatch(r"ld(64)?(-linux|-musl)?(-.+)?\.so(\..+)?", os.path.basename(lib)):
                        continue
            if name[:10] in ('linux-gate', 'linux-vdso'):
                # linux-gate is a fake library which does not exist and should be ignored. See also:
                # http://www.trilithium.com/johan/2005/08/linux-gate/
                continue

            if compat.is_cygwin:
                # exclude Windows system library
                if lib.lower().startswith('/cygdrive/c/windows/system'):
                    continue

            # Reset library path if it does not exist
            if not os.path.exists(lib):
                lib = None
        elif line.endswith("not found"):
            # On glibc-based linux distributions, missing libraries are marked with name.so => not found
            tokens = line.split('=>')
            if len(tokens) != 2:
                continue
            name = tokens[0].strip()
            lib = None
        else:
            # TODO: should we warn about unprocessed lines?
            continue

        # Fall back to searching the supplied search paths, if any.
        if not lib:
            lib = _resolve_library_path_in_search_paths(
                os.path.basename(name),  # Search for basename of the referenced name.
                search_paths,
            )

        # Normalize the resolved path, to remove any extraneous "../" elements.
        if lib:
            lib = os.path.normpath(lib)

        # Return referenced name as-is instead of computing a basename, to provide additional context when library
        # cannot be resolved.
        output.add((name, lib))

    return output


def _get_imports_macholib(filename, search_paths):
    """
    macOS-specific helper for `get_imports`, which uses `macholib` to analyze library load commands in Mach-O headers.
    """
    from macholib.dyld import dyld_find
    from macholib.mach_o import LC_RPATH
    from macholib.MachO import MachO

    try:
        from macholib.dyld import _dyld_shared_cache_contains_path
    except ImportError:
        _dyld_shared_cache_contains_path = None

    output = set()

    # Parent directory of the input binary and parent directory of python executable, used to substitute @loader_path
    # and @executable_path. The macOS dylib loader (dyld) fully resolves the symbolic links when using @loader_path
    # and @executable_path references, so we need to do the same using `os.path.realpath`.
    bin_path = os.path.dirname(os.path.realpath(filename))
    python_bin = os.path.realpath(sys.executable)
    python_bin_path = os.path.dirname(python_bin)

    def _get_referenced_libs(m):
        # Collect referenced libraries from MachO object.
        referenced_libs = set()
        for header in m.headers:
            for idx, name, lib in header.walkRelocatables():
                referenced_libs.add(lib)
        return referenced_libs

    def _get_run_paths(m):
        # Find LC_RPATH commands to collect rpaths from MachO object.
        # macholib does not handle @rpath, so we need to handle run paths ourselves.
        run_paths = []
        for header in m.headers:
            for command in header.commands:
                # A command is a tuple like:
                #   (<macholib.mach_o.load_command object at 0x>,
                #    <macholib.mach_o.rpath_command object at 0x>,
                #    '../lib\x00\x00')
                cmd_type = command[0].cmd
                if cmd_type == LC_RPATH:
                    rpath = command[2].decode('utf-8')
                    # Remove trailing '\x00' characters. E.g., '../lib\x00\x00'
                    rpath = rpath.rstrip('\x00')
                    # If run path starts with @, ensure it starts with either @loader_path or @executable_path.
                    # We cannot process anything else.
                    if rpath.startswith("@") and not rpath.startswith(("@executable_path", "@loader_path")):
                        logger.warning("Unsupported rpath format %r found in binary %r - ignoring...", rpath, filename)
                        continue
                    run_paths.append(rpath)
        return run_paths

    @functools.lru_cache
    def get_run_paths_and_referenced_libs(filename):
        # Walk through Mach-O headers, and collect all referenced libraries and run paths.
        m = MachO(filename)
        return _get_referenced_libs(m), _get_run_paths(m)

    @functools.lru_cache
    def get_run_paths(filename):
        # Walk through Mach-O headers, and collect only run paths.
        return _get_run_paths(MachO(filename))

    # Collect referenced libraries and run paths from the input binary.
    referenced_libs, run_paths = get_run_paths_and_referenced_libs(filename)

    # On macOS, run paths (rpaths) are inherited from the executable that loads the given shared library (or from the
    # shared library that loads the given shared library). This means that shared libraries and python binary extensions
    # can reference other shared libraries using @rpath without having set any run paths themselves.
    #
    # In order to simulate the run path inheritance that happens in unfrozen python programs, we need to augment the
    # run paths from the given binary with those set by the python interpreter executable (`sys.executable`). Anaconda
    # python, for example, sets the run path on the python executable to `@loader_path/../lib`, which allows python
    # extensions to reference shared libraries in the Anaconda environment's `lib` directory via only `@rpath`
    # (for example, the `_ssl` extension can reference the OpenSSL library as `@rpath/libssl.3.dylib`). In another
    # example, python executable has its run path set to the top-level directory of its .framework bundle; in this
    # case the `ssl` extension references the OpenSSL library as `@rpath/Versions/3.10/lib/libssl.1.1.dylib`.
    run_paths += get_run_paths(python_bin)

    # This fallback should be fully superseded by the above recovery of run paths from python executable; but for now,
    # keep it around in case of unforeseen corner cases.
    run_paths.append(os.path.join(compat.base_prefix, 'lib'))

    # De-duplicate run_paths while preserving their order.
    run_paths = list(dict.fromkeys(run_paths))

    def _resolve_using_path(lib):
        # Absolute paths should not be resolved; we should just check whether the library exists or not. This used to
        # be done using macholib's dyld_find() as well (as it properly handles system libraries that are hidden on
        # Big Sur and later), but it turns out that even if given an absolute path, it gives precedence to search paths
        # from DYLD_LIBRARY_PATH. This leads to confusing errors when directory in DYLD_LIBRARY_PATH contains a file
        # (shared library or data file) that happens to have the same name as a library from a system framework.
        if os.path.isabs(lib):
            if _dyld_shared_cache_contains_path is not None and _dyld_shared_cache_contains_path(lib):
                return lib
            if os.path.isfile(lib):
                return lib
            return None

        try:
            return dyld_find(lib)
        except ValueError:
            return None

    def _resolve_using_loader_path(lib, bin_path, python_bin_path):
        # Strictly speaking, @loader_path should be anchored to parent directory of analyzed binary (`bin_path`), while
        # @executable_path should be anchored to the parent directory of the process' executable. Typically, this would
        # be python executable (`python_bin_path`). Unless we are analyzing a collected 3rd party executable; in that
        # case, `bin_path` is correct option. So we first try resolving using `bin_path`, and then fall back to
        # `python_bin_path`. This does not account for transitive run paths of higher-order dependencies, but there is
        # only so much we can do here...
        #
        # NOTE: do not use macholib's `dyld_find`, because its fallback search locations might end up resolving wrong
        # instance of the library! For example, if our `bin_path` and `python_bin_path` are anchored in an Anaconda
        # python environment and the candidate library path does not exit (because we are calling this function when
        # trying to resolve @rpath with multiple candidate run paths), we do not want to fall back to eponymous library
        # that happens to be present in the Homebrew python environment...
        if lib.startswith('@loader_path/'):
            lib = lib[len('@loader_path/'):]
        elif lib.startswith('@executable_path/'):
            lib = lib[len('@executable_path/'):]

        # Try resolving with binary's path first...
        resolved_lib = _resolve_using_path(os.path.join(bin_path, lib))
        if resolved_lib is not None:
            return resolved_lib

        # ... and fall-back to resolving with python executable's path
        return _resolve_using_path(os.path.join(python_bin_path, lib))

    # Try to resolve full path of the referenced libraries.
    for referenced_lib in referenced_libs:
        resolved_lib = None

        # If path starts with @rpath, we have to handle it ourselves.
        if referenced_lib.startswith('@rpath'):
            lib = os.path.join(*referenced_lib.split(os.sep)[1:])  # Remove the @rpath/ prefix

            # Try all run paths.
            for run_path in run_paths:
                # Join the path.
                lib_path = os.path.join(run_path, lib)

                if lib_path.startswith(("@executable_path", "@loader_path")):
                    # Run path starts with @executable_path or @loader_path.
                    lib_path = _resolve_using_loader_path(lib_path, bin_path, python_bin_path)
                else:
                    # If run path was relative, anchor it to binary's location.
                    if not os.path.isabs(lib_path):
                        os.path.join(bin_path, lib_path)
                    lib_path = _resolve_using_path(lib_path)

                if lib_path and os.path.exists(lib_path):
                    resolved_lib = lib_path
                    break
        else:
            if referenced_lib.startswith(("@executable_path", "@loader_path")):
                resolved_lib = _resolve_using_loader_path(referenced_lib, bin_path, python_bin_path)
            else:
                resolved_lib = _resolve_using_path(referenced_lib)

        # Fall back to searching the supplied search paths, if any.
        if not resolved_lib:
            resolved_lib = _resolve_library_path_in_search_paths(
                os.path.basename(referenced_lib),  # Search for basename of the referenced name.
                search_paths,
            )

        # Normalize the resolved path, to remove any extraneous "../" elements.
        if resolved_lib:
            resolved_lib = os.path.normpath(resolved_lib)

        # Return referenced library name as-is instead of computing a basename. Full referenced name carries additional
        # information that might be useful for the caller to determine how to deal with unresolved library (e.g., ignore
        # unresolved libraries that are supposed to be located in system-wide directories).
        output.add((referenced_lib, resolved_lib))

    return output


#- Library full path resolution


def resolve_library_path(name, search_paths=None):
    """
    Given a library name, attempt to resolve full path to that library. The search for library is done via
    platform-specific mechanism and fall back to optionally-provided list of search paths. Returns None if library
    cannot be resolved. If give library name is already an absolute path, the given path is returned without any
    processing.
    """
    # No-op if path is already absolute.
    if os.path.isabs(name):
        return name

    if compat.is_unix:
        # Use platform-specific helper.
        fullpath = _resolve_library_path_unix(name)
        if fullpath:
            return fullpath
        # Fall back to searching the supplied search paths, if any
        return _resolve_library_path_in_search_paths(name, search_paths)
    elif compat.is_win:
        # Try the caller-supplied search paths, if any.
        fullpath = _resolve_library_path_in_search_paths(name, search_paths)
        if fullpath:
            return fullpath

        # Fall back to default Windows search paths, using the PATH environment variable (which should also include
        # the system paths, such as c:\windows and c:\windows\system32)
        win_search_paths = [path for path in compat.getenv('PATH', '').split(os.pathsep) if path]
        return _resolve_library_path_in_search_paths(name, win_search_paths)
    else:
        return ctypes.util.find_library(name)

    return None


# Compatibility aliases for hooks from contributed hooks repository. All of these now point to the high-level
# `resolve_library_path`.
findLibrary = resolve_library_path
findSystemLibrary = resolve_library_path


def _resolve_library_path_in_search_paths(name, search_paths=None):
    """
    Low-level helper for resolving given library name to full path in given list of search paths.
    """
    for search_path in search_paths or []:
        fullpath = os.path.join(search_path, name)
        if not os.path.isfile(fullpath):
            continue

        # On Windows, ensure that architecture matches that of running python interpreter.
        if compat.is_win:
            try:
                dll_machine_type = winutils.get_pe_file_machine_type(fullpath)
            except Exception:
                # A search path might contain a DLL that we cannot analyze; for example, a stub file. Skip over.
                continue
            if dll_machine_type != _exe_machine_type:
                continue

        return os.path.normpath(fullpath)

    return None


def _resolve_library_path_unix(name):
    """
    UNIX-specific helper for resolving library path.

    Emulates the algorithm used by dlopen. `name` must include the prefix, e.g., ``libpython2.4.so``.
    """
    assert compat.is_unix, "Current implementation for Unix only (Linux, Solaris, AIX, FreeBSD)"

    if name.endswith('.so') or '.so.' in name:
        # We have been given full library name that includes suffix. Use `_resolve_library_path_in_search_paths` to find
        # the exact match.
        lib_search_func = _resolve_library_path_in_search_paths
    else:
        # We have been given a library name without suffix. Use `_which_library` as search function, which will try to
        # find library with matching basename.
        lib_search_func = _which_library

    # Look in the LD_LIBRARY_PATH according to platform.
    if compat.is_aix:
        lp = compat.getenv('LIBPATH', '')
    elif compat.is_darwin:
        lp = compat.getenv('DYLD_LIBRARY_PATH', '')
    else:
        lp = compat.getenv('LD_LIBRARY_PATH', '')
    lib = lib_search_func(name, filter(None, lp.split(os.pathsep)))

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
            paths.extend(['/lib32', '/usr/lib32'])
        else:
            paths.extend(['/lib64', '/usr/lib64'])
        # Machine dependent locations.
        if compat.machine == 'intel':
            if compat.architecture == '32bit':
                paths.extend(['/usr/lib/i386-linux-gnu'])
            else:
                paths.extend(['/usr/lib/x86_64-linux-gnu'])

        # On Debian/Ubuntu /usr/bin/python is linked statically with libpython. Newer Debian/Ubuntu with multiarch
        # support puts the libpythonX.Y.so in paths like /usr/lib/i386-linux-gnu/. Try to query the arch-specific
        # sub-directory, if available.
        arch_subdir = sysconfig.get_config_var('multiarchsubdir')
        if arch_subdir:
            arch_subdir = os.path.basename(arch_subdir)
            paths.append(os.path.join('/usr/lib', arch_subdir))
        else:
            logger.debug('Multiarch directory not detected.')

        # Termux (a Ubuntu like subsystem for Android) has an additional libraries directory.
        if os.path.isdir('/data/data/com.termux/files/usr/lib'):
            paths.append('/data/data/com.termux/files/usr/lib')

        if compat.is_aix:
            paths.append('/opt/freeware/lib')
        elif compat.is_hpux:
            if compat.architecture == '32bit':
                paths.append('/usr/local/lib/hpux32')
            else:
                paths.append('/usr/local/lib/hpux64')
        elif compat.is_freebsd or compat.is_openbsd:
            paths.append('/usr/local/lib')
        lib = lib_search_func(name, paths)

    return lib


def _which_library(name, dirs):
    """
    Search for a shared library in a list of directories.

    Args:
        name:
            The library name including the `lib` prefix but excluding any `.so` suffix.
        dirs:
            An iterable of folders to search in.
    Returns:
        The path to the library if found or None otherwise.

    """
    matcher = _library_matcher(name)
    for path in filter(os.path.exists, dirs):
        for _path in os.listdir(path):
            if matcher(_path):
                return os.path.join(path, _path)


def _library_matcher(name):
    """
    Create a callable that matches libraries if **name** is a valid library prefix for input library full names.
    """
    return re.compile(name + r"[0-9]*\.").match


#- Python shared library search


def get_python_library_path():
    """
    Find Python shared library that belongs to the current interpreter.

    Return  full path to Python dynamic library or None when not found.

    PyInstaller needs to collect the Python shared library, so that bootloader can load it, import Python C API
    symbols, and use them to set up the embedded Python interpreter.

    The name of the shared library is typically fixed (`python3.X.dll` on Windows, libpython3.X.so on Unix systems,
    and `libpython3.X.dylib` on macOS for shared library builds and `Python.framework/Python` for framework build).
    Its location can usually be inferred from the Python interpreter executable, when the latter is dynamically
    linked against the shared library.

    However, some situations require extra handling due to various quirks; for example, Debian-based linux
    distributions statically link the Python interpreter executable against the Python library, while also providing
    a shared library variant for external users.
    """

    # With Windows Python builds, this is pretty straight-forward: `sys.dllhandle` provides a handle to the loaded
    # Python DLL, and we can resolve its path using `GetModuleFileName()` from win32 API.
    # This is applicable to python.org Windows builds, Anaconda on Windows, and MSYS2 Python.
    if compat.is_win:
        if hasattr(sys, 'dllhandle'):
            import _winapi
            return _winapi.GetModuleFileName(sys.dllhandle)
        else:
            raise PythonLibraryNotFoundError(
                "Python was built without a shared library, which is required by PyInstaller."
            )

    # On other (POSIX) platforms, the name of the Python shared library is available in the `INSTSONAME` variable
    # exposed by the `sysconfig` module. There is also the `LDLIBRARY` variable, which points to the unversioned .so
    # symbolic link for linking purposes; however, we are interested in the actual, fully-versioned soname.
    # This should cover all variations in the naming schemes across different platforms as well as different build
    # options (debug build, free-threaded build, etc.).
    #
    # However, `INSTSONAME` points to the shared library only if shared library is enabled; in static-library builds,
    # it points to the static library, which is of no use to us. We can check if Python was built with shared library
    # (i.e., the `--enable-shared` option) by checking `Py_ENABLE_SHARED` variable, which should be set to 1 in this
    # case (and 0 in the case of a static-library build). On macOS, builds made with `--enable-framework` have
    # `Py_ENABLE_SHARED` set to 0, but have `PYTHONFRAMEWORK`set to a non-empty string.
    #
    # The above description is further complicated by the fact that in some Python builds, the `python` executable is
    # built against static Python library, and the shared library is built separately and provided for development and
    # for embedders (such as PyInstaller). Presumably, this is done for performance reasons. Also, it is enabled by the
    # fact that on POSIX, Python extensions do not need to have the referenced Python symbols resolved at link-time;
    # rather, these symbols can be resolved at run-time from the running Python process (and are effectively provided
    # by the `python` executable). Such builds come in two variants. In the first variant, `Py_ENABLE_SHARED` is 0 and
    # `INSTSONAME` points to the static library; an example of such build is Anaconda Python. In the second variant,
    # `Py_ENABLE_SHARED` is 1 and `INSTSONAME` points to the shared library, but `python` executable is not linked
    # against it; examples of such build are Debian-packaged Python and `astral-sh/python-build-standalone` Python.
    #
    # Therefore, our strategy is as follows: if we determine that shared library was enabled (via `Py_ENABLE_SHARED`
    # on all platforms and/or via `PYTHONFRAMEWORK` on macOS), we use the name given by `INSTSONAME`. First, we try
    # to locate it by analyzing binary dependencies of `python` executable (regular shared-library-enabled build),
    # then fall back to standard search locations (second variant of static-executable-with-separate-shared-library).
    # If `Py_ENABLE_SHARED` is set to 0, we try to guess the library name based on version and feature flags, but we
    # search only `sys.base_prefix` and `lib` directory under `sys.base_prefix`; if the shared library is not found
    # there, we assume it is unavailable and raise an error. This attempts to accommodate Anaconda python (and corner
    # cases when we cannot reliably identify Anaconda python - see #9273) and prevent accidental bundling of
    # system-wide Python shared library in cases when user tries to use custom Python build without shared library.

    def _find_lib_in_libdirs(name, *libdirs):
        for libdir in libdirs:
            full_path = os.path.join(libdir, name)
            if not os.path.exists(full_path):
                continue
            # Resolve potential symbolic links to achieve consistent results with linker-based search; e.g., on
            # POSIX systems, linker resolves unversioned library names (python3.X.so) to versioned ones
            # (libpython3.X.so.1.0) due to former being symbolic links to the latter. See #6831.
            full_path = os.path.realpath(full_path)
            if not os.path.exists(full_path):
                continue
            return full_path
        return None

    is_shared = (
        # Builds made with `--enable-shared` have `Py_ENABLE_SHARED` set to 1. This is true even for Debian-packaged
        # Python, which has the `python` executable statically linked against the Python library.
        sysconfig.get_config_var("Py_ENABLE_SHARED") or
        # On macOS, builds made with `--enable-framework` have `Py_ENABLE_SHARED` set to 0, but have `PYTHONFRAMEWORK`
        # set to a non-empty string.
        (compat.is_darwin and sysconfig.get_config_var("PYTHONFRAMEWORK"))
    )

    if not is_shared:
        # Anaconda Python; this codepath used to be under `compat.is_conda` switch, but we may also be dealing with
        # Anaconda Python without `conda-meta` directory (see #9273). Or some other Python build where shared library
        # is provided but `Py_ENABLE_SHARED` is set to 0.
        py_major, py_minor = sys.version_info[:2]
        py_suffix = "t" if compat.is_nogil else ""  # TODO: does Anaconda provide debug builds with "d" suffix?
        if compat.is_darwin:
            # macOS
            expected_name = f"libpython{py_major}.{py_minor}{py_suffix}.dylib"
        else:
            # Linux; assume any other potential POSIX builds use the same naming scheme.
            expected_name = f"libpython{py_major}.{py_minor}{py_suffix}.so.1.0"

        # Allow the library to be only in `sys.base_prefix` or the `lib` directory under it. This should prevent us from
        # picking up an unrelated copy of shared library that might happen to be available in standard search path, when
        # we should instead be raising an error due to Python having been built without a shared library. (In true
        # static-library builds, Python's own extension modules are usually turned into built-ins. So picking up an
        # unrelated Python shared library that happens to be of the same version results in run-time errors due to
        # missing extensions - because in the build that produced the shared library, those extensions are expected to
        # be external extension modules!)
        python_libname = _find_lib_in_libdirs(
            expected_name,  # Full name
            compat.base_prefix,
            os.path.join(compat.base_prefix, 'lib'),
        )
        if python_libname:
            return python_libname

        # Raise PythonLibraryNotFoundError
        option_str = (
            "either the `--enable-shared` or the `--enable-framework` option"
            if compat.is_darwin else "the `--enable-shared` option"
        )
        raise PythonLibraryNotFoundError(
            "Python was built without a shared library, which is required by PyInstaller. "
            f"If you built Python from source, rebuild it with {option_str}."
        )

    # Use the library name from `INSTSONAME`.
    expected_name = sysconfig.get_config_var('INSTSONAME')

    # In Cygwin builds (and also MSYS2 python, although that should be handled by Windows-specific codepath...),
    # INSTSONAME is available, but the name has a ".dll.a" suffix; remove that trailing ".a".
    if (compat.is_win or compat.is_cygwin) and os.path.normcase(expected_name).endswith('.dll.a'):
        expected_name = expected_name[:-2]

    # NOTE: on macOS with .framework bundle build, INSTSONAME contains full name of the .framework library, for example
    # `Python.framework/Versions/3.13/Python`. Pre-compute a basename for comparisons that are using only basename.
    expected_basename = os.path.normcase(os.path.basename(expected_name))

    # First, try to find the expected name among the libraries against which the Python executable is linked. This
    # assumes that the Python executable was not statically linked against the library (as is the case with
    # Debian-packaged Python or `astral-sh/python-build-standalone` Python).
    imported_libraries = get_imports(compat.python_executable)  # (name, fullpath) tuples
    for _, lib_path in imported_libraries:
        if lib_path is None:
            continue  # Skip unresolved imports
        if os.path.normcase(os.path.basename(lib_path)) == expected_basename:  # Basename comparison
            # Python library found. Return absolute path to it.
            return lib_path

    # As a fallback, try to find the library in several "standard" search locations...

    # First, search the `sys.base_prefix` and `lib` directory in `sys.base_prefix`, as these locations have the closest
    # ties to our current Python process. This caters to builds such as `astral-sh/python-build-standalone` Python.
    python_libname = _find_lib_in_libdirs(
        expected_name,  # Full name
        compat.base_prefix,
        os.path.join(compat.base_prefix, 'lib'),
    )
    if python_libname:
        return python_libname

    # Perform search in the configured library search locations. This should be done after exhausting all other options;
    # it primarily caters to Debian-packaged Python, but we need to make sure that we do not collect shared library from
    # system-installed Python when the current interpreter is in fact some other Python build (such as, for example,
    # `astral-sh/python-build-standalone` Python that is handled in the preceding code block).
    python_libname = resolve_library_path(expected_basename)  # Basename
    if python_libname:
        return python_libname

    # Not found. Raise a PythonLibraryNotFoundError with corresponding message.
    message = f"ERROR: Python shared library ({expected_name!r}) was not found!"
    if compat.is_linux and os.path.isfile('/etc/debian_version'):
        # The shared library is provided by `libpython3.x` package (i.e., no need to install full `python3-dev`).
        pkg_name = f"libpython3.{sys.version_info.minor}"
        message += (
            " If you are using system python on Debian/Ubuntu, you might need to install a separate package by running "
            f"`apt install {pkg_name}`."
        )

    raise PythonLibraryNotFoundError(message)


#- Binary vs data (re)classification


def classify_binary_vs_data(filename):
    """
    Classify the given file as either BINARY or a DATA, using appropriate platform-specific method. Returns 'BINARY'
    or 'DATA' string depending on the determined file type, or None if classification cannot be performed (non-existing
    file, missing tool, and other errors during classification).
    """

    # We cannot classify non-existent files.
    if not os.path.isfile(filename):
        return None

    # Use platform-specific implementation.
    return _classify_binary_vs_data(filename)


if compat.is_linux:

    def _classify_binary_vs_data(filename):
        # First check for ELF signature, in order to avoid calling `objdump` on every data file, which can be costly.
        try:
            with open(filename, 'rb') as fp:
                sig = fp.read(4)
        except Exception:
            return None

        if sig != b"\x7FELF":
            return "DATA"

        # Verify the binary by checking if `objdump` recognizes the file. The preceding ELF signature check should
        # ensure that this is an ELF file, while this check should ensure that it is a valid ELF file. In the future,
        # we could try checking that the architecture matches the running platform.
        cmd_args = ['objdump', '-a', filename]
        try:
            p = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                encoding='utf8',
            )
        except Exception:
            return None  # Failed to run `objdump` or `objdump` unavailable.

        return 'BINARY' if p.returncode == 0 else 'DATA'

elif compat.is_win:

    @functools.lru_cache()
    def _no_op_pefile_gc():
        # Disable pefile's reduntant and very slow call to gc.collect(). See #8762.
        import types
        import gc
        import pefile

        fake_gc = types.ModuleType("gc")
        fake_gc.__dict__.update(gc.__dict__)
        fake_gc.collect = lambda *_, **__: None
        pefile.gc = fake_gc

    def _classify_binary_vs_data(filename):
        import pefile

        _no_op_pefile_gc()

        # First check for MZ signature, which should allow us to quickly classify the majority of data files.
        try:
            with open(filename, 'rb') as fp:
                sig = fp.read(2)
        except Exception:
            return None

        if sig != b"MZ":
            return "DATA"

        # Check if the file can be opened using `pefile`.
        try:
            with pefile.PE(filename, fast_load=True) as pe:  # noqa: F841
                pass
            return 'BINARY'
        except pefile.PEFormatError:
            return 'DATA'
        except Exception:
            pass

        return None

elif compat.is_darwin:

    def _classify_binary_vs_data(filename):
        # See if the file can be opened using `macholib`.
        import macholib.MachO

        try:
            macho = macholib.MachO.MachO(filename)  # noqa: F841
            return 'BINARY'
        except Exception:
            # TODO: catch only `ValueError`?
            pass

        return 'DATA'

else:

    def _classify_binary_vs_data(filename):
        # Classification not implemented for the platform.
        return None
