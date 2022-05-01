#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import copy
import os
import sys
import textwrap
from pathlib import Path
from typing import Callable, Tuple

import pkg_resources

from PyInstaller import HOMEPATH, compat
from PyInstaller import log as logging
from PyInstaller.exceptions import ExecCommandFailed
from PyInstaller.utils.hooks.win32 import \
    get_pywin32_module_file_attribute  # noqa: F401
from PyInstaller import isolated

logger = logging.getLogger(__name__)

# These extensions represent Python executables and should therefore be ignored when collecting data files.
# NOTE: .dylib files are not Python executable and should not be in this list.
PY_IGNORE_EXTENSIONS = set(compat.ALL_SUFFIXES)

# Some hooks need to save some values. This is the dict that can be used for that.
#
# When running tests this variable should be reset before every test.
#
# For example the 'wx' module needs variable 'wxpubsub'. This tells PyInstaller which protocol of the wx module
# should be bundled.
hook_variables = {}


def __exec_python_cmd(cmd, env=None, capture_stdout=True):
    """
    Executes an externally spawned Python interpreter. If capture_stdout is set to True, returns anything that was
    emitted in the standard output as a single string. Otherwise, returns the exit code.
    """
    # 'PyInstaller.config' cannot be imported as other top-level modules.
    from PyInstaller.config import CONF
    if env is None:
        env = {}
    # Update environment. Defaults to 'os.environ'
    pp_env = copy.deepcopy(os.environ)
    pp_env.update(env)
    # Prepend PYTHONPATH with pathex.
    # Some functions use some PyInstaller code in subprocess, so add PyInstaller HOMEPATH to sys.path as well.
    pp = os.pathsep.join(CONF['pathex'] + [HOMEPATH])

    # PYTHONPATH might be already defined in the 'env' argument or in the original 'os.environ'. Prepend it.
    if 'PYTHONPATH' in pp_env:
        pp = os.pathsep.join([pp_env.get('PYTHONPATH'), pp])
    pp_env['PYTHONPATH'] = pp

    if capture_stdout:
        txt = compat.exec_python(*cmd, env=pp_env)
        return txt.strip()
    else:
        return compat.exec_python_rc(*cmd, env=pp_env)


def __exec_statement(statement, capture_stdout=True):
    statement = textwrap.dedent(statement)
    cmd = ['-c', statement]
    return __exec_python_cmd(cmd, capture_stdout=capture_stdout)


def exec_statement(statement):
    """
    Execute a single Python statement in an externally-spawned interpreter, and return the resulting standard output
    as a string.

    Examples::

        tk_version = exec_statement("from _tkinter import TK_VERSION; print(TK_VERSION)")

        mpl_data_dir = exec_statement("import matplotlib; print(matplotlib.get_data_path())")
        datas = [ (mpl_data_dir, "") ]

    Notes:
        As of v4.6.0, usage of this function is discouraged in favour of the
        new :mod:`PyInstaller.isolated` module.

    """
    return __exec_statement(statement, capture_stdout=True)


def exec_statement_rc(statement):
    """
    Executes a Python statement in an externally spawned interpreter, and returns the exit code.
    """
    return __exec_statement(statement, capture_stdout=False)


def __exec_script(script_filename, *args, env=None, capture_stdout=True):
    """
    Executes a Python script in an externally spawned interpreter. If capture_stdout is set to True, returns anything
    that was emitted in the standard output as a single string. Otherwise, returns the exit code.

    To prevent misuse, the script passed to utils.hooks.exec_script must be located in the
    `PyInstaller/utils/hooks/subproc` directory.
    """
    script_filename = os.path.basename(script_filename)
    script_filename = os.path.join(os.path.dirname(__file__), 'subproc', script_filename)
    if not os.path.exists(script_filename):
        raise SystemError(
            "To prevent misuse, the script passed to PyInstaller.utils.hooks.exec_script must be located in the "
            "`PyInstaller/utils/hooks/subproc` directory."
        )

    cmd = [script_filename]
    cmd.extend(args)
    return __exec_python_cmd(cmd, env=env, capture_stdout=capture_stdout)


def exec_script(script_filename, *args, env=None):
    """
    Executes a Python script in an externally spawned interpreter, and returns anything that was emitted to the standard
    output as a single string.

    To prevent misuse, the script passed to utils.hooks.exec_script must be located in the
    `PyInstaller/utils/hooks/subproc` directory.
    """
    return __exec_script(script_filename, *args, env=env, capture_stdout=True)


def exec_script_rc(script_filename, *args, env=None):
    """
    Executes a Python script in an externally spawned interpreter, and returns the exit code.

    To prevent misuse, the script passed to utils.hooks.exec_script must be located in the
    `PyInstaller/utils/hooks/subproc` directory.
    """
    return __exec_script(script_filename, *args, env=env, capture_stdout=False)


def eval_statement(statement):
    """
    Execute a single Python statement in an externally-spawned interpreter, and :func:`eval` its output (if any).

    Example::

      databases = eval_statement('''
         import sqlalchemy.databases
         print(sqlalchemy.databases.__all__)
         ''')
      for db in databases:
         hiddenimports.append("sqlalchemy.databases." + db)

    Notes:
        As of v4.6.0, usage of this function is discouraged in favour of the
        new :mod:`PyInstaller.isolated` module.

    """
    txt = exec_statement(statement).strip()
    if not txt:
        # Return an empty string, which is "not true" but is iterable.
        return ''
    return eval(txt)


def eval_script(scriptfilename, *args, env=None):
    txt = exec_script(scriptfilename, *args, env=env).strip()
    if not txt:
        # Return an empty string, which is "not true" but is iterable.
        return ''
    return eval(txt)


@isolated.decorate
def get_pyextension_imports(module_name):
    """
    Return list of modules required by binary (C/C++) Python extension.

    Python extension files ends with .so (Unix) or .pyd (Windows). It is almost impossible to analyze binary extension
    and its dependencies.

    Module cannot be imported directly.

    Let's at least try import it in a subprocess and observe the difference in module list from sys.modules.

    This function could be used for 'hiddenimports' in PyInstaller hooks files.
    """
    import sys
    import importlib

    original = set(sys.modules.keys())

    # When importing this module - sys.modules gets updated.
    importlib.import_module(module_name)

    # Find and return which new modules have been loaded.
    return list(set(sys.modules.keys()) - original - {module_name})


def get_homebrew_path(formula=''):
    """
    Return the homebrew path to the requested formula, or the global prefix when called with no argument.

    Returns the path as a string or None if not found.
    """
    import subprocess
    brewcmd = ['brew', '--prefix']
    path = None
    if formula:
        brewcmd.append(formula)
        dbgstr = 'homebrew formula "%s"' % formula
    else:
        dbgstr = 'homebrew prefix'
    try:
        path = subprocess.check_output(brewcmd).strip()
        logger.debug('Found %s at "%s"' % (dbgstr, path))
    except OSError:
        logger.debug('Detected homebrew not installed')
    except subprocess.CalledProcessError:
        logger.debug('homebrew formula "%s" not installed' % formula)
    if path:
        return path.decode('utf8')  # Mac OS filenames are UTF-8
    else:
        return None


def remove_prefix(string, prefix):
    """
    This function removes the given prefix from a string, if the string does indeed begin with the prefix; otherwise,
    it returns the original string.
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string


def remove_suffix(string, suffix):
    """
    This function removes the given suffix from a string, if the string does indeed end with the suffix; otherwise,
    it returns the original string.
    """
    # Special case: if suffix is empty, string[:0] returns ''. So, test for a non-empty suffix.
    if suffix and string.endswith(suffix):
        return string[:-len(suffix)]
    else:
        return string


# TODO: Do we really need a helper for this? This is pretty trivially obvious.
def remove_file_extension(filename):
    """
    This function returns filename without its extension.

    For Python C modules it removes even whole '.cpython-34m.so' etc.
    """
    for suff in compat.EXTENSION_SUFFIXES:
        if filename.endswith(suff):
            return filename[0:filename.rfind(suff)]
    # Fallback to ordinary 'splitext'.
    return os.path.splitext(filename)[0]


@isolated.decorate
def can_import_module(module_name):
    """
    Check if the specified module can be imported.

    Intended as a silent module availability check, as it does not print ModuleNotFoundError traceback to stderr when
    the module is unavailable.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of the module.

    Returns
    ----------
    bool
        Boolean indicating whether the module can be imported or not.
    """
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


# TODO: Replace most calls to exec_statement() with calls to this function.
def get_module_attribute(module_name, attr_name):
    """
    Get the string value of the passed attribute from the passed module if this attribute is defined by this module
    _or_ raise `AttributeError` otherwise.

    Since modules cannot be directly imported during analysis, this function spawns a subprocess importing this module
    and returning the string value of this attribute in this module.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of this module.
    attr_name : str
        Name of the attribute in this module to be retrieved.

    Returns
    ----------
    str
        String value of this attribute.

    Raises
    ----------
    AttributeError
        If this attribute is undefined.
    """
    @isolated.decorate
    def _get_module_attribute(module_name, attr_name):
        import importlib
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)

    # Return AttributeError on any kind of errors, to preserve old behavior.
    try:
        return _get_module_attribute(module_name, attr_name)
    except Exception as e:
        raise AttributeError(f"Failed to retrieve attribute {attr_name} from module {module_name}") from e


def get_module_file_attribute(package):
    """
    Get the absolute path to the specified module or package.

    Modules and packages *must not* be directly imported in the main process during the analysis. Therefore, to
    avoid leaking the imports, this function uses an isolated subprocess when it needs to import the module and
    obtain its ``__file__`` attribute.

    Parameters
    ----------
    package : str
        Fully-qualified name of module or package.

    Returns
    ----------
    str
        Absolute path of this module.
    """
    # First, try to use 'pkgutil'. It is the fastest way, but does not work on certain modules in pywin32 that replace
    # all module attributes with those of the .dll. In addition, we need to avoid it for submodules/subpackages,
    # because it ends up importing their parent package, which would cause an import leak during the analysis.
    filename = None
    if '.' not in package:
        try:
            import pkgutil
            loader = pkgutil.find_loader(package)
            filename = loader.get_filename(package)
            # Apparently in the past, ``None`` could be returned for built-in ``datetime`` module. Just in case this
            # is still possible, return only if filename is valid.
            if filename:
                return filename
        except (AttributeError, ImportError):
            pass

    # Second attempt: try to obtain module/package's __file__ attribute in an isolated subprocess.
    @isolated.decorate
    def _get_module_file_attribute(package):
        # First try to use 'pkgutil'; it returns the filename even if the module or package cannot be imported
        # (e.g., C-extension module with missing dependencies).
        try:
            import pkgutil
            loader = pkgutil.find_loader(package)
            filename = loader.get_filename(package)
            # Safe-guard against ``None`` being returned (see comment in the non-isolated codepath).
            if filename:
                return filename
        except (AttributeError, ImportError):
            pass

        # Fall back to import attempt
        import importlib
        p = importlib.import_module(package)
        return p.__file__

    # The old behavior was to return ImportError (and that is what the test are also expecting...).
    try:
        filename = _get_module_file_attribute(package)
    except Exception as e:
        raise ImportError(f"Failed to obtain the __file__ attribute of package/module {package}!") from e

    return filename


def is_module_satisfies(requirements, version=None, version_attr='__version__'):
    """
    Test if a :pep:`0440` requirement is installed.

    Parameters
    ----------
    requirements : str
        Requirements in `pkg_resources.Requirements.parse()` format.
    version : str
        Optional PEP 0440-compliant version (e.g., `3.14-rc5`) to be used _instead_ of the current version of this
        module. If non-`None`, this function ignores all `setuptools` distributions for this module and instead
        compares this version against the version embedded in the passed requirements. This ignores the module name
        embedded in the passed requirements, permitting arbitrary versions to be compared in a robust manner.
        See examples below.
    version_attr : str
        Optional name of the version attribute defined by this module, defaulting to `__version__`. If a
        `setuptools` distribution exists for this module (it usually does) _and_ the `version` parameter is `None`
        (it usually is), this parameter is ignored.

    Returns
    ----------
    bool
        Boolean result of the desired validation.

    Raises
    ----------
    AttributeError
        If no `setuptools` distribution exists for this module _and_ this module defines no attribute whose name is the
        passed `version_attr` parameter.
    ValueError
        If the passed specification does _not_ comply with `pkg_resources.Requirements`_ syntax.

    Examples
    --------

    ::

        # Assume PIL 2.9.0, Sphinx 1.3.1, and SQLAlchemy 0.6 are all installed.
        >>> from PyInstaller.utils.hooks import is_module_satisfies
        >>> is_module_satisfies('sphinx >= 1.3.1')
        True
        >>> is_module_satisfies('sqlalchemy != 0.6')
        False

        >>> is_module_satisfies('sphinx >= 1.3.1; sqlalchemy != 0.6')
        False


        # Compare two arbitrary versions. In this case, the module name "sqlalchemy" is simply ignored.
        >>> is_module_satisfies('sqlalchemy != 0.6', version='0.5')
        True

        # Since the "pillow" project providing PIL publishes its version via the custom "PILLOW_VERSION" attribute
        # (rather than the standard "__version__" attribute), an attribute name is passed as a fallback to validate PIL
        # when not installed by setuptools. As PIL is usually installed by setuptools, this optional parameter is
        # usually ignored.
        >>> is_module_satisfies('PIL == 2.9.0', version_attr='PILLOW_VERSION')
        True

    .. seealso::

        `pkg_resources.Requirements`_ for the syntax details.

    .. _`pkg_resources.Requirements`:
            https://pythonhosted.org/setuptools/pkg_resources.html#id12
    """
    # If no version was explicitly passed...
    if version is None:
        # If a setuptools distribution exists for this module, this validation is a simple one-liner. This approach
        # supports non-version validation (e.g., of "["- and "]"-delimited extras) and is hence preferable.
        try:
            pkg_resources.get_distribution(requirements)
        # If no such distribution exists, fall back to the logic below.
        except pkg_resources.DistributionNotFound:
            pass
        # If all existing distributions violate these requirements, fail.
        except (pkg_resources.UnknownExtra, pkg_resources.VersionConflict):
            return False
        # Else, an existing distribution satisfies these requirements. Win!
        else:
            return True

    # Either a module version was explicitly passed or no setuptools distribution exists for this module. First, parse a
    # setuptools "Requirements" object from this requirements string.
    requirements_parsed = pkg_resources.Requirement.parse(requirements)

    # If no version was explicitly passed, query this module for it.
    if version is None:
        module_name = requirements_parsed.project_name
        if can_import_module(module_name):
            version = get_module_attribute(module_name, version_attr)
        else:
            version = None

    if not version:
        # Module does not exist in the system.
        return False
    else:
        # Compare this version against the one parsed from the requirements.
        return version in requirements_parsed


def is_package(module_name):
    """
    Check if a Python module is really a module or is a package containing other modules, without importing anything
    in the main process.

    :param module_name: Module name to check.
    :return: True if module is a package else otherwise.
    """
    def _is_package(module_name):
        """
        Determines whether the given name represents a package or not. If the name represents a top-level module or
        a package, it is not imported. If the name represents a sub-module or a sub-package, its parent is imported.
        In such cases, this function should be called from an isolated suprocess.
        """
        try:
            import importlib.util
            spec = importlib.util.find_spec(module_name)
            return bool(spec.submodule_search_locations)
        except Exception:
            return False

    # For top-level packages/modules, we can perform check in the main process; otherwise, we need to isolate the
    # call to prevent import leaks in the main process.
    if '.' not in module_name:
        return _is_package(module_name)
    else:
        return isolated.call(_is_package, module_name)


def get_all_package_paths(package):
    """
    Given a package name, return all paths associated with the package. Typically, packages have a single location
    path, but PEP 420 namespace packages may be split across multiple locations. Returns an empty list if the specified
    package is not found or is not a package.
    """
    def _get_package_paths(package):
        """
        Retrieve package path(s), as advertised by submodule_search_paths attribute of the spec obtained via
        importlib.util.find_spec(package). If the name represents a top-level package, the package is not imported.
        If the name represents a sub-module or a sub-package, its parent is imported. In such cases, this function
        should be called from an isolated suprocess. Returns an empty list if specified package is not found or is not
        a package.
        """
        try:
            import importlib.util
            spec = importlib.util.find_spec(package)
            if not spec or not spec.submodule_search_locations:
                return []
            return [str(path) for path in spec.submodule_search_locations]
        except Exception:
            return []

    # For top-level packages/modules, we can perform check in the main process; otherwise, we need to isolate the
    # call to prevent import leaks in the main process.
    if '.' not in package:
        pkg_paths = _get_package_paths(package)
    else:
        pkg_paths = isolated.call(_get_package_paths, package)

    return pkg_paths


def package_base_path(package_path, package):
    """
    Given a package location path and package name, return the package base path, i.e., the directory in which the
    top-level package is located. For example, given the path ``/abs/path/to/python/libs/pkg/subpkg`` and
    package name ``pkg.subpkg``, the function returns ``/abs/path/to/python/libs``.
    """
    return remove_suffix(package_path, package.replace('.', os.sep))  # Base directory


def get_package_paths(package):
    """
    Given a package, return the path to packages stored on this machine and also returns the path to this particular
    package. For example, if pkg.subpkg lives in /abs/path/to/python/libs, then this function returns
    ``(/abs/path/to/python/libs, /abs/path/to/python/libs/pkg/subpkg)``.

    NOTE: due to backwards compatibility, this function returns only one package path along with its base directory.
    In case of PEP 420 namespace package with multiple location, only first location is returned. To obtain all
    package paths, use the ``get_all_package_paths`` function and obtain corresponding base directories using the
    ``package_base_path`` helper.
    """
    pkg_paths = get_all_package_paths(package)
    if not pkg_paths:
        raise ValueError(f"Package '{package}' does not exist or is not a package!")

    if len(pkg_paths) > 1:
        logger.warning(
            "get_package_paths - package %s has multiple paths (%r); returning only first one!", package, pkg_paths
        )

    pkg_dir = pkg_paths[0]
    pkg_base = package_base_path(pkg_dir, package)

    return pkg_base, pkg_dir


def collect_submodules(package: str, filter: Callable[[str], bool] = lambda name: True, on_error="warn once"):
    """
    List all submodules of a given package.

    Arguments:
        package:
            An ``import``-able package.
        filter:
            Filter the submodules found: A callable that takes a submodule name and returns True if it should be
            included.
        on_error:
            The action to take when a submodule fails to import. May be any of:

            - raise: Errors are reraised and terminate the build.
            - warn: Errors are downgraded to warnings.
            - warn once: The first error issues a warning but all
              subsequent errors are ignored to minimise *stderr pollution*. This
              is the default.
            - ignore: Skip all errors. Don't warn about anything.
    Returns:
        All submodules to be assigned to ``hiddenimports`` in a hook.

    This function is intended to be used by hook scripts, not by main PyInstaller code.

    Examples::

        # Collect all submodules of Sphinx don't contain the word ``test``.
        hiddenimports = collect_submodules(
            "Sphinx", ``filter=lambda name: 'test' not in name)

    .. versionchanged:: 4.5
        Add the **on_error** parameter.

    """
    # Accept only strings as packages.
    if not isinstance(package, compat.string_types):
        raise TypeError('package must be a str')
    if on_error not in ("ignore", "warn once", "warn", "raise"):
        raise ValueError(
            f"Invalid on-error action '{on_error}': Must be one of ('ignore', 'warn once', 'warn', 'raise')"
        )

    logger.debug('Collecting submodules for %s' % package)
    # Skip a module which is not a package.
    if not is_package(package):
        logger.debug('collect_submodules - Module %s is not a package.' % package)
        return []

    # Determine the filesystem path(s) to the specified package.
    pkg_dirs = get_all_package_paths(package)
    modules = []
    for pkg_dir in pkg_dirs:
        modules += _collect_submodules(pkg_dir, package, on_error)

    # Apply the user defined filter function. Filter out duplicates at the same time.
    modules = [i for i in set(modules) if filter(i)]

    logger.debug("collect_submodules - Found submodules: %s", modules)
    return modules


@isolated.decorate
def _collect_submodules(pkg_dir, package, on_error):
    import sys
    import pkgutil
    from traceback import format_exception_only
    from collections import deque

    # ``pkgutil.walk_packages`` doesn't walk subpackages of zipped files per https://bugs.python.org/issue14209. This is
    # a workaround.
    seen = set()
    todo = deque([([pkg_dir], package + ".")])
    modules = [package]

    while todo:
        path, prefix = todo.pop()
        for importer, name, ispkg in pkgutil.iter_modules(path, prefix):
            if not name.startswith(prefix):
                name = prefix + name
            modules.append(name)

            if not ispkg:
                # Only packages can have submodules.
                continue

            try:
                __import__(name)
            except Exception as ex:
                # Catch all errors then either raise, warn or ignore them as determined by the *on_error* parameter.
                if on_error in ("warn", "warn once"):
                    from PyInstaller.log import logger
                    ex = "".join(format_exception_only(type(ex), ex)).strip()
                    logger.warning(f"Failed to collect submodules for '{name}' because importing '{name}' raised: {ex}")
                    if on_error == "warn once":
                        on_error = "ignore"
                elif on_error == "raise":
                    raise ImportError(f"Unable to load submodule '{name}'.") from ex
                # Don't attempt to recurse to submodules if this module didn't even make it into sys.modules.
                if name not in sys.modules:
                    continue
            path = getattr(sys.modules[name], '__path__', None) or []

            # Don't traverse path items we've seen before.
            path = [p for p in path if p not in seen]
            seen.update(path)
            todo.append((path, name + '.'))

    return modules


def is_module_or_submodule(name, mod_or_submod):
    """
    This helper function is designed for use in the ``filter`` argument of :func:`collect_submodules`, by returning
    ``True`` if the given ``name`` is a module or a submodule of ``mod_or_submod``.

    Examples:

        The following excludes ``foo.test`` and ``foo.test.one`` but not ``foo.testifier``. ::

            collect_submodules('foo', lambda name: not is_module_or_submodule(name, 'foo.test'))``
    """
    return name.startswith(mod_or_submod + '.') or name == mod_or_submod


# Patterns of dynamic library filenames that might be bundled with some installed Python packages.
PY_DYLIB_PATTERNS = [
    '*.dll',
    '*.dylib',
    'lib*.so',
]


def collect_dynamic_libs(package, destdir=None):
    """
    This function produces a list of (source, dest) of dynamic library files that reside in package. Its output can be
    directly assigned to ``binaries`` in a hook script. The package parameter must be a string which names the package.

    :param destdir: Relative path to ./dist/APPNAME where the libraries should be put.
    """
    logger.debug('Collecting dynamic libraries for %s' % package)

    # Accept only strings as packages.
    if not isinstance(package, compat.string_types):
        raise TypeError('package must be a str')

    # Skip a module which is not a package.
    if not is_package(package):
        logger.warning(
            "collect_dynamic_libs - skipping library collection for module '%s' as it is not a package.", package
        )
        return []

    pkg_dirs = get_all_package_paths(package)
    dylibs = []
    for pkg_dir in pkg_dirs:
        pkg_base = package_base_path(pkg_dir, package)
        # Recursively glob for all file patterns in the package directory
        for pattern in PY_DYLIB_PATTERNS:
            files = Path(pkg_dir).rglob(pattern)
            for source in files:
                # Produce the tuple ('/abs/path/to/source/mod/submod/file.pyd', 'mod/submod')
                if destdir:
                    # Put libraries in the specified target directory.
                    dest = destdir
                else:
                    # Preserve original directory hierarchy.
                    dest = source.parent.relative_to(pkg_base)
                logger.debug(' %s, %s' % (source, dest))
                dylibs.append((str(source), str(dest)))

    return dylibs


def collect_data_files(package, include_py_files=False, subdir=None, excludes=None, includes=None):
    r"""
    This function produces a list of ``(source, dest)`` non-Python (i.e., data) files that reside in ``package``.
    Its output can be directly assigned to ``datas`` in a hook script; for example, see ``hook-sphinx.py``.
    Parameters:

    -   The ``package`` parameter is a string which names the package.
    -   By default, all Python executable files (those ending in ``.py``, ``.pyc``, and so on) will NOT be collected;
        setting the ``include_py_files`` argument to ``True`` collects these files as well. This is typically used with
        Python functions (such as those in ``pkgutil``) that search a given directory for Python executable files and
        load them as extensions or plugins.
    -   The ``subdir`` argument gives a subdirectory relative to ``package`` to search, which is helpful when submodules
        are imported at run-time from a directory lacking ``__init__.py``.
    -   The ``excludes`` argument contains a sequence of strings or Paths. These provide a list of
        `globs <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_
        to exclude from the collected data files; if a directory matches the provided glob, all files it contains will
        be excluded as well. All elements must be relative paths, which are relative to the provided package's path
        (/ ``subdir`` if provided).

        Therefore, ``*.txt`` will exclude only ``.txt`` files in ``package``\ 's path, while ``**/*.txt`` will exclude
        all ``.txt`` files in ``package``\ 's path and all its subdirectories. Likewise, ``**/__pycache__`` will exclude
        all files contained in any subdirectory named ``__pycache__``.
    -   The ``includes`` function like ``excludes``, but only include matching paths. ``excludes`` override
        ``includes``: a file or directory in both lists will be excluded.

    This function does not work on zipped Python eggs.

    This function is intended to be used by hook scripts, not by main PyInstaller code.
    """
    logger.debug('Collecting data files for %s' % package)

    # Accept only strings as packages.
    if not isinstance(package, compat.string_types):
        raise TypeError('package must be a str')

    # Skip a module which is not a package.
    if not is_package(package):
        logger.warning("collect_data_files - skipping data collection for module '%s' as it is not a package.", package)
        return []

    # Make sure the excludes are a list; this also makes a copy, so we don't modify the original.
    excludes = list(excludes) if excludes else []
    # These excludes may contain directories which need to be searched.
    excludes_len = len(excludes)
    # Including py files means don't exclude them. This pattern will search any directories for containing files, so
    # do not modify ``excludes_len``.
    if not include_py_files:
        excludes += ['**/*' + s for s in compat.ALL_SUFFIXES]

    # Exclude .pyo files if include_py_files is False.
    if not include_py_files and ".pyo" not in compat.ALL_SUFFIXES:
        excludes.append('**/*.pyo')

    # If not specified, include all files. Follow the same process as the excludes.
    includes = list(includes) if includes else ["**/*"]
    includes_len = len(includes)

    # A helper function to glob the in/ex "cludes", adding a wildcard to refer to all files under a subdirectory if a
    # subdirectory is matched by the first ``clude_len`` patterns. Otherwise, it in/excludes the matched file.
    # **This modifies** ``cludes``.
    def clude_walker(
        # Package directory to scan
        pkg_dir,
        # A list of paths relative to ``pkg_dir`` to in/exclude.
        cludes,
        # The number of ``cludes`` for which matching directories should be searched for all files under them.
        clude_len,
        # True if the list is includes, False for excludes.
        is_include
    ):
        for i, c in enumerate(cludes):
            for g in Path(pkg_dir).glob(c):
                if g.is_dir():
                    # Only files are sources. Subdirectories are not.
                    if i < clude_len:
                        # In/exclude all files under a matching subdirectory.
                        cludes.append(str((g / "**/*").relative_to(pkg_dir)))
                else:
                    # In/exclude a matching file.
                    sources.add(g) if is_include else sources.discard(g)

    # Obtain all paths for the specified package, and process each path independently.
    datas = []

    pkg_dirs = get_all_package_paths(package)
    for pkg_dir in pkg_dirs:
        sources = set()  # Reset sources set

        pkg_base = package_base_path(pkg_dir, package)
        if subdir:
            pkg_dir = os.path.join(pkg_dir, subdir)

        # Process the package path with clude walker
        clude_walker(pkg_dir, includes, includes_len, True)
        clude_walker(pkg_dir, excludes, excludes_len, False)

        # Transform the sources into tuples for ``datas``.
        datas += [(str(s), str(s.parent.relative_to(pkg_base))) for s in sources]

    logger.debug("collect_data_files - Found files: %s", datas)
    return datas


def collect_system_data_files(path, destdir=None, include_py_files=False):
    """
    This function produces a list of (source, dest) non-Python (i.e., data) files that reside somewhere on the system.
    Its output can be directly assigned to ``datas`` in a hook script.

    This function is intended to be used by hook scripts, not by main PyInstaller code.
    """
    # Accept only strings as paths.
    if not isinstance(path, compat.string_types):
        raise TypeError('path must be a str')

    # Walk through all file in the given package, looking for data files.
    datas = []
    for dirpath, dirnames, files in os.walk(path):
        for f in files:
            extension = os.path.splitext(f)[1]
            if include_py_files or (extension not in PY_IGNORE_EXTENSIONS):
                # Produce the tuple: (/abs/path/to/source/mod/submod/file.dat, mod/submod/destdir)
                source = os.path.join(dirpath, f)
                dest = str(Path(dirpath).relative_to(path))
                if destdir is not None:
                    dest = os.path.join(destdir, dest)
                datas.append((source, dest))

    return datas


def copy_metadata(package_name, recursive=False):
    """
    Collect distribution metadata so that ``pkg_resources.get_distribution()`` can find it.

    This function returns a list to be assigned to the ``datas`` global variable. This list instructs PyInstaller to
    copy the metadata for the given package to the frozen application's data directory.

    Parameters
    ----------
    package_name : str
        Specifies the name of the package for which metadata should be copied.
    recursive : bool
        If true, collect metadata for the package's dependencies too. This enables use of
        ``pkg_resources.require('package')`` inside the frozen application.

    Returns
    -------
    list
        This should be assigned to ``datas``.

    Examples
    --------
        >>> from PyInstaller.utils.hooks import copy_metadata
        >>> copy_metadata('sphinx')
        [('c:\\python27\\lib\\site-packages\\Sphinx-1.3.2.dist-info',
          'Sphinx-1.3.2.dist-info')]


    Some packages rely on metadata files accessed through the ``pkg_resources`` module. Normally PyInstaller does not
    include these metadata files. If a package fails without them, you can use this function in a hook file to easily
    add them to the frozen bundle. The tuples in the returned list have two strings. The first is the full pathname to a
    folder in this system. The second is the folder name only. When these tuples are added to ``datas``\\ , the folder
    will be bundled at the top level.

    .. versionchanged:: 4.3.1

        Prevent ``dist-info`` metadata folders being renamed to ``egg-info`` which broke ``pkg_resources.require`` with
        *extras* (see :issue:`#3033`).

    .. versionchanged:: 4.4.0

        Add the **recursive** option.
    """
    from collections import deque

    todo = deque([package_name])
    done = set()
    out = []

    while todo:
        package_name = todo.pop()
        if package_name in done:
            continue

        dist = pkg_resources.get_distribution(package_name)
        if dist.egg_info is not None:
            # If available, dist.egg_info points to the source .egg-info or .dist-info directory.
            dest = _copy_metadata_dest(dist.egg_info, dist.project_name)
            out.append((dist.egg_info, dest))
        else:
            # When .egg-info is not a directory but a single file, dist.egg_info is None, and we need to resolve the
            # path ourselves. This format is common on Ubuntu/Debian with their deb-packaged python packages.
            dist_src = _resolve_legacy_metadata_path(dist)
            if dist_src is None:
                raise RuntimeError(
                    f"No metadata path found for distribution '{dist.project_name}' (legacy fallback search failed)."
                )
            out.append((dist_src, '.'))  # It is a file, so dest path needs to be '.'

        if not recursive:
            return out
        done.add(package_name)
        todo.extend(i.project_name for i in dist.requires())

    return out


def _normalise_dist(name: str) -> str:
    return name.lower().replace("_", "-")


def _resolve_legacy_metadata_path(dist):
    """
    Attempt to resolve the legacy metadata file for the given distribution.
    The .egg-info file is commonly used by Debian/Ubuntu when packaging python packages.

    Args:
        dist:
            The distribution information as returned by ``pkg_resources.get_distribution("xyz")``.
    Returns:
        The path to the distribution's metadata file.
    """

    candidates = [
        # This fallback was in place in pre-#5774 times. However, it is insufficient, because dist.egg_name() may be
        # greenlet-0.4.15-py3.8 (Ubuntu 20.04 package) while the file we are searching for is greenlet-0.4.15.egg-info.
        f"{dist.egg_name()}.egg-info",
        # The extra name-version.egg-info path format
        f"{dist.project_name}-{dist.version}.egg-info",
        # And the name_with_underscores-version.egg-info.format
        f"{dist.project_name.replace('-', '_')}-{dist.version}.egg-info",
    ]

    # As an additional attempt, try to remove the-pyX.Y suffix from egg name.
    pyxx_suffix = f"-py{sys.version_info[0]}.{sys.version_info[1]}"
    if dist.egg_name().endswith(pyxx_suffix):
        candidates.append(dist.egg_name()[:-len(pyxx_suffix)] + ".egg-info")

    for candidate in candidates:
        candidate_path = os.path.join(dist.location, candidate)
        if os.path.isfile(candidate_path):
            return candidate_path

    return None


def _copy_metadata_dest(egg_path: str, project_name: str) -> str:
    """
    Choose an appropriate destination path for a distribution's metadata.

    Args:
        egg_path:
            The output of ``pkg_resources.get_distribution("xyz").egg_info``: a full path to the source
            ``xyz-version.dist-info`` or ``xyz-version.egg-info`` folder containing package metadata.
        project_name:
            The distribution name given.
    Returns:
        The *dest* parameter: where in the bundle should this folder go.
    Raises:
        RuntimeError:
            If **egg_path** is None, i.e., no metadata is found.
    """
    if egg_path is None:
        # According to older implementations of this function, packages may have no metadata. I have no idea how this
        # can happen...
        raise RuntimeError(f"No metadata path found for distribution '{project_name}'.")

    egg_path = Path(egg_path)
    _project_name = _normalise_dist(project_name)

    # There has been a fair amount of whack-a-mole fixing to this step. If new cases appear which this function cannot
    # handle, add them to the corresponding test:
    #   tests/unit/test_hookutils.py::test_copy_metadata_dest()
    # See there also for example input/outputs.

    # The most obvious answer is that the metadata folder should have the same name in a PyInstaller build as it does
    # normally::
    if _normalise_dist(egg_path.name).startswith(_project_name):
        # e.g., .../lib/site-packages/xyz-1.2.3.dist-info
        return egg_path.name

    # Using just the base-name breaks for an egg_path of the form:
    #   '.../site-packages/xyz-version.win32.egg/EGG-INFO'
    # because multiple collected metadata folders will be written to the same name 'EGG-INFO' and clobber each other
    # (see #1888). In this case, the correct behaviour appears to be to use the last two parts of the path:
    if len(egg_path.parts) >= 2:
        if _normalise_dist(egg_path.parts[-2]).startswith(_project_name):
            return os.path.join(*egg_path.parts[-2:])

    # This is something unheard of.
    raise RuntimeError(
        f"Unknown metadata type '{egg_path}' from the '{project_name}' distribution. Please report this at "
        f"https://github/pyinstaller/pyinstaller/issues."
    )


def get_installer(module):
    """
    Try to find which package manager installed a module.

    :param module: Module to check
    :return: Package manager or None
    """
    file_name = get_module_file_attribute(module)
    site_dir = file_name[:file_name.index('site-packages') + len('site-packages')]
    # This is necessary for situations where the project name and module name do not match, e.g.,
    # pyenchant (project name) vs. enchant (module name).
    pkgs = pkg_resources.find_distributions(site_dir)
    package = None
    for pkg in pkgs:
        if module.lower() in pkg.key:
            package = pkg
            break
    metadata_dir, dest_dir = copy_metadata(package)[0]
    # Check for an INSTALLER file in the metedata_dir and return the first line which should be the program that
    # installed the module.
    installer_file = os.path.join(metadata_dir, 'INSTALLER')
    if os.path.isdir(metadata_dir) and os.path.exists(installer_file):
        with open(installer_file, 'r') as installer_file_object:
            lines = installer_file_object.readlines()
            if lines[0] != '':
                installer = lines[0].rstrip('\r\n')
                logger.debug(
                    "Found installer: '{0}' for module: '{1}' from package: '{2}'".format(installer, module, package)
                )
                return installer
    if compat.is_darwin:
        try:
            output = compat.exec_command_stdout('port', 'provides', file_name)
            if 'is provided by' in output:
                logger.debug(
                    "Found installer: 'macports' for module: '{0}' from package: '{1}'".format(module, package)
                )
                return 'macports'
        except ExecCommandFailed:
            pass
        real_path = os.path.realpath(file_name)
        if 'Cellar' in real_path:
            logger.debug("Found installer: 'homebrew' for module: '{0}' from package: '{1}'".format(module, package))
            return 'homebrew'
    return None


# ``_map_distribution_to_packages`` is expensive. Compute it when used, then return the memoized value. This is a simple
# alternative to ``functools.lru_cache``.
def _memoize(f):
    memo = []

    def helper():
        if not memo:
            memo.append(f())
        return memo[0]

    return helper


# Walk through every package, determining to which distribution it belongs.
@_memoize
def _map_distribution_to_packages():
    logger.info('Determining a mapping of distributions to packages...')
    dist_to_packages = {}
    for p in sys.path:
        # The path entry ``''`` refers to the current directory.
        if not p:
            p = '.'
        # Ignore any entries in ``sys.path`` that do not exist.
        try:
            lds = os.listdir(p)
        except Exception:
            pass
        else:
            for ld in lds:
                # Not all packages belong to a distribution. Skip these.
                try:
                    dist = pkg_resources.get_distribution(ld)
                except Exception:
                    pass
                else:
                    dist_to_packages.setdefault(dist.key, []).append(ld)

    return dist_to_packages


# Given a ``package_name`` as a string, this function returns a list of packages needed to satisfy the requirements.
# This output can be assigned directly to ``hiddenimports``.
def requirements_for_package(package_name):
    hiddenimports = []

    dist_to_packages = _map_distribution_to_packages()
    for requirement in pkg_resources.get_distribution(package_name).requires():
        if requirement.key in dist_to_packages:
            required_packages = dist_to_packages[requirement.key]
            hiddenimports.extend(required_packages)
        else:
            logger.warning(
                'Unable to find package for requirement %s from package %s.', requirement.project_name, package_name
            )

    logger.info('Packages required by %s:\n%s', package_name, hiddenimports)
    return hiddenimports


def collect_all(
    package_name,
    include_py_files=True,
    filter_submodules=None,
    exclude_datas=None,
    include_datas=None,
    on_error="warn once",
) -> Tuple[list, list, list]:
    """
    Collect everything for a given package name.

    Arguments:
        package_name:
            An ``import``-able package name.
        include_py_files:
            Forwarded to :func:`collect_data_files`.
        filter_submodules:
            Forwarded to :func:`collect_submodules`.
        exclude_datas:
            Forwarded to :func:`collect_data_files`.
        include_datas:
            Forwarded to :func:`collect_data_files`.
        on_error:
            Forwarded onto :func:`collect_submodules`.

    Returns:
        tuple: A ``(datas, binaries, hiddenimports)`` triplet containing:

        - All data files, raw Python files (if **include_py_files**), and package metadata folders.
        - All dynamic libraries as returned by :func:`collect_dynamic_libs`.
        - All submodules of **packagename** and its dependencies.

    Typical use::

        datas, binaries, hiddenimports = collect_all('my_module_name')
    """
    datas = []
    try:
        datas += copy_metadata(package_name)
    except Exception as e:
        logger.warning('Unable to copy metadata for %s: %s', package_name, e)
    datas += collect_data_files(package_name, include_py_files, excludes=exclude_datas, includes=include_datas)
    binaries = collect_dynamic_libs(package_name)
    if filter_submodules:
        hiddenimports = collect_submodules(package_name, on_error=on_error, filter=filter_submodules)
    else:
        hiddenimports = collect_submodules(package_name)
    try:
        hiddenimports += requirements_for_package(package_name)
    except Exception as e:
        logger.warning('Unable to determine requirements for %s: %s', package_name, e)

    return datas, binaries, hiddenimports


def collect_entry_point(name: str) -> Tuple[list, list]:
    """
    Collect modules and metadata for all exporters of a given entry point.

    Args:
        name:
            The name of the entry point. Check the documentation for the library that uses the entry point to find
            its name.
    Returns:
        A ``(datas, hiddenimports)`` pair that should be assigned to the ``datas`` and ``hiddenimports``, respectively.

    For libraries, such as ``pytest`` or ``keyring``, that rely on plugins to extend their behaviour.

    Examples:
        Pytest uses an entry point called ``'pytest11'`` for its extensions.
        To collect all those extensions use::

            datas, hiddenimports = collect_entry_point("pytest11")

        These values may be used in a hook or added to the ``datas`` and ``hiddenimports`` arguments in the ``.spec``
        file. See :ref:`using spec files`.

    .. versionadded:: 4.3
    """
    import pkg_resources
    datas = []
    imports = []
    for dist in pkg_resources.iter_entry_points(name):
        datas += copy_metadata(dist.dist.project_name)
        imports.append(dist.module_name)
    return datas, imports


def get_hook_config(hook_api, module_name, key):
    """
    Get user settings for hooks.

    Args:
        module_name:
            The module/package for which the key setting belong to.
        key:
            A key for the config.
    Returns:
        The value for the config. ``None`` if not set.

    The ``get_hook_config`` function will lookup settings in the ``Analysis.hooksconfig`` dict.

    The hook settings can be added to ``.spec`` file in the form of::

        a = Analysis(["my-app.py"],
            ...
            hooksconfig = {
                "gi": {
                    "icons": ["Adwaita"],
                    "themes": ["Adwaita"],
                    "languages": ["en_GB", "zh_CN"],
                },
            },
            ...
        )
    """
    config = hook_api.analysis.hooksconfig
    value = None
    if module_name in config and key in config[module_name]:
        value = config[module_name][key]
    return value


if compat.is_pure_conda:
    from PyInstaller.utils.hooks import conda as conda_support  # noqa: F401
elif compat.is_conda:
    from PyInstaller.utils.hooks.conda import CONDA_META_DIR as _tmp
    logger.warning(
        "Assuming this is not an Anaconda environment or an additional venv/pipenv/... environment manager is being "
        "used on top, because the conda-meta folder %s does not exist.", _tmp
    )
    del _tmp
