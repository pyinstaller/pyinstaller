#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import copy
import glob
import os
import pkg_resources
import pkgutil
import sys
import textwrap
from pathlib import Path

from ...compat import base_prefix, exec_command_stdout, exec_python, \
    exec_python_rc, is_darwin, is_venv, string_types, open_file, \
    EXTENSION_SUFFIXES, ALL_SUFFIXES, is_conda, is_pure_conda
from ... import HOMEPATH
from ... import log as logging
from ...exceptions import ExecCommandFailed

logger = logging.getLogger(__name__)

# These extensions represent Python executables and should therefore be
# ignored when collecting data files.
# NOTE: .dylib files are not Python executable and should not be in this list.
PY_IGNORE_EXTENSIONS = set(ALL_SUFFIXES)

# Some hooks need to save some values. This is the dict that can be used for
# that.
#
# When running tests this variable should be reset before every test.
#
# For example the 'wx' module needs variable 'wxpubsub'. This tells PyInstaller
# which protocol of the wx module should be bundled.
hook_variables = {}


def __exec_python_cmd(cmd, env=None, capture_stdout=True):
    """
    Executes an externally spawned Python interpreter. If capture_stdout
    is set to True, returns anything that was emitted in the standard
    output as a single string. Otherwise, returns the exit code.
    """
    # 'PyInstaller.config' cannot be imported as other top-level modules.
    from ...config import CONF
    if env is None:
        env = {}
    # Update environment. Defaults to 'os.environ'
    pp_env = copy.deepcopy(os.environ)
    pp_env.update(env)
    # Prepend PYTHONPATH with pathex
    # Some functions use some PyInstaller code in subprocess so add
    # PyInstaller HOMEPATH to sys.path too.
    pp = os.pathsep.join(CONF['pathex'] + [HOMEPATH])

    # PYTHONPATH might be already defined in the 'env' argument or in
    # the original 'os.environ'. Prepend it.
    if 'PYTHONPATH' in pp_env:
        pp = os.pathsep.join([pp_env.get('PYTHONPATH'), pp])
    pp_env['PYTHONPATH'] = pp

    if capture_stdout:
        txt = exec_python(*cmd, env=pp_env)
        return txt.strip()
    else:
        return exec_python_rc(*cmd, env=pp_env)


def __exec_statement(statement, capture_stdout=True):
    statement = textwrap.dedent(statement)
    cmd = ['-c', statement]
    return __exec_python_cmd(cmd, capture_stdout=capture_stdout)


def exec_statement(statement):
    """
    Executes a Python statement in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a single string.
    """
    return __exec_statement(statement, capture_stdout=True)


def exec_statement_rc(statement):
    """
    Executes a Python statement in an externally spawned interpreter, and
    returns the exit code.
    """
    return __exec_statement(statement, capture_stdout=False)


def __exec_script(script_filename, *args, env=None, capture_stdout=True):
    """
    Executes a Python script in an externally spawned interpreter. If
    capture_stdout is set to True, returns anything that was emitted in
    the standard output as a single string. Otherwise, returns the exit
    code.

    To prevent misuse, the script passed to utils.hooks.exec_script
    must be located in the `PyInstaller/utils/hooks/subproc` directory.
    """
    script_filename = os.path.basename(script_filename)
    script_filename = os.path.join(os.path.dirname(__file__), 'subproc', script_filename)
    if not os.path.exists(script_filename):
        raise SystemError("To prevent misuse, the script passed to "
                          "PyInstaller.utils.hooks.exec_script must be located "
                          "in the `PyInstaller/utils/hooks/subproc` directory.")

    cmd = [script_filename]
    cmd.extend(args)
    return __exec_python_cmd(cmd, env=env, capture_stdout=capture_stdout)


def exec_script(script_filename, *args, env=None):
    """
    Executes a Python script in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a
    single string.

    To prevent misuse, the script passed to utils.hooks.exec_script
    must be located in the `PyInstaller/utils/hooks/subproc` directory.
    """
    return __exec_script(script_filename, *args, env=env, capture_stdout=True)


def exec_script_rc(script_filename, *args, env=None):
    """
    Executes a Python script in an externally spawned interpreter, and
    returns the exit code.

    To prevent misuse, the script passed to utils.hooks.exec_script
    must be located in the `PyInstaller/utils/hooks/subproc` directory.
    """
    return __exec_script(script_filename, *args, env=env, capture_stdout=False)


def eval_statement(statement):
    txt = exec_statement(statement).strip()
    if not txt:
        # return an empty string which is "not true" but iterable
        return ''
    return eval(txt)


def eval_script(scriptfilename, *args, env=None):
    txt = exec_script(scriptfilename, *args, env=env).strip()
    if not txt:
        # return an empty string which is "not true" but iterable
        return ''
    return eval(txt)


def get_pyextension_imports(modname):
    """
    Return list of modules required by binary (C/C++) Python extension.

    Python extension files ends with .so (Unix) or .pyd (Windows).
    It's almost impossible to analyze binary extension and its dependencies.

    Module cannot be imported directly.

    Let's at least try import it in a subprocess and get the difference
    in module list from sys.modules.

    This function could be used for 'hiddenimports' in PyInstaller hooks files.
    """

    statement = """
        import sys
        # Importing distutils filters common modules, especially in virtualenv.
        import distutils
        original_modlist = set(sys.modules.keys())
        # When importing this module - sys.modules gets updated.
        import %(modname)s
        all_modlist = set(sys.modules.keys())
        diff = all_modlist - original_modlist
        # Module list contain original modname. We do not need it there.
        diff.discard('%(modname)s')
        # Print module list to stdout.
        print(list(diff))
    """ % {'modname': modname}
    module_imports = eval_statement(statement)

    if not module_imports:
        logger.error('Cannot find imports for module %s' % modname)
        return []  # Means no imports found or looking for imports failed.
    # module_imports = filter(lambda x: not x.startswith('distutils'), module_imports)
    return module_imports


def get_homebrew_path(formula=''):
    """
    Return the homebrew path to the requested formula, or the global prefix when
    called with no argument.  Returns the path as a string or None if not found.
    :param formula:
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
        return path.decode('utf8')  # OS X filenames are UTF-8
    else:
        return None


def remove_prefix(string, prefix):
    """
    This function removes the given prefix from a string, if the string does
    indeed begin with the prefix; otherwise, it returns the string
    unmodified.
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string


def remove_suffix(string, suffix):
    """
    This function removes the given suffix from a string, if the string
    does indeed end with the prefix; otherwise, it returns the string
    unmodified.
    """
    # Special case: if suffix is empty, string[:0] returns ''. So, test
    # for a non-empty suffix.
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
    for suff in EXTENSION_SUFFIXES:
        if filename.endswith(suff):
            return filename[0:filename.rfind(suff)]
    # Fallback to ordinary 'splitext'.
    return os.path.splitext(filename)[0]


def can_import_module(module_name):
    """
    Check if the specified module can be imported.

    Intended as a silent module availability check, as it does not print
    ModuleNotFoundError traceback to stderr when the module is unavailable.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of the module.

    Returns
    ----------
    bool
        Boolean indicating whether the module can be imported or not.
    """

    rc = exec_statement_rc("""
        try:
            import {0}
        except ModuleNotFoundError:
            raise SystemExit(1)
        """.format(module_name)
    )
    return rc == 0


# TODO: Replace most calls to exec_statement() with calls to this function.
def get_module_attribute(module_name, attr_name):
    """
    Get the string value of the passed attribute from the passed module if this
    attribute is defined by this module _or_ raise `AttributeError` otherwise.

    Since modules cannot be directly imported during analysis, this function
    spawns a subprocess importing this module and returning the string value of
    this attribute in this module.

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
    # Magic string to be printed and captured below if this attribute is
    # undefined, which should be sufficiently obscure as to avoid collisions
    # with actual attribute values. That's the hope, anyway.
    attr_value_if_undefined = '!)ABadCafe@(D15ea5e#*DeadBeef$&Fee1Dead%^'
    attr_value = exec_statement("""
        import %s as m
        print(getattr(m, %r, %r))
    """ % (module_name, attr_name, attr_value_if_undefined))

    if attr_value == attr_value_if_undefined:
        raise AttributeError(
            'Module %r has no attribute %r' % (module_name, attr_name))
    else:
        return attr_value


def get_module_file_attribute(package):
    """
    Get the absolute path of the module with the passed name.

    Since modules *cannot* be directly imported during analysis, this function
    spawns a subprocess importing this module and returning the value of this
    module's `__file__` attribute.

    Parameters
    ----------
    package : str
        Fully-qualified name of this module.

    Returns
    ----------
    str
        Absolute path of this module.
    """
    # First try to use 'pkgutil'. - fastest but doesn't work on
    # certain modules in pywin32, which replace all module attributes
    # with those of the .dll
    try:
        loader = pkgutil.find_loader(package)
        attr = loader.get_filename(package)
        # The built-in ``datetime`` module returns ``None``. Mark this as
        # an ``ImportError``.
        if not attr:
            raise ImportError('Unable to load module attributes')
    # Second try to import module in a subprocess. Might raise ImportError.
    except (AttributeError, ImportError) as e:
        # Statement to return __file__ attribute of a package.
        __file__statement = """
            import %s as p
            try:
                print(p.__file__)
            except:
                # If p lacks a file attribute, hide the exception.
                pass
        """
        attr = exec_statement(__file__statement % package)
        if not attr.strip():
            raise ImportError('Unable to load module attribute') from e
    return attr


def is_module_satisfies(requirements, version=None, version_attr='__version__'):
    """
    `True` if the module, package, or C extension described by the passed
    requirements string both exists and satisfies these requirements.

    This function checks module versions and extras (i.e., optional install-
    time features) via the same low-level algorithm leveraged by
    `easy_install` and `pip`, and should _always_ be called in lieu of manual
    checking. Attempting to manually check versions and extras invites subtle
    issues, particularly when comparing versions lexicographically (e.g.,
    `'00.5' > '0.6'` is `True`, despite being semantically untrue).

    Requirements
    ----------
    This function is typically used to compare the version of a currently
    installed module with some desired version. To do so, a string of the form
    `{module_name} {comparison_operator} {version}` (e.g., `sphinx >= 1.3`) is
    passed as the `requirements` parameter, where:

    * `{module_name}` is the fully-qualified name of the module, package, or C
      extension to be tested (e.g., `yaml`). This is _not_ a `setuptools`-
      specific distribution name (e.g., `PyYAML`).
    * `{comparison_operator}` is the numeric comparison to be performed. All
      numeric Python comparisons are supported (e.g., `!=`, `==`, `<`, `>=`).
    * `{version}` is the desired PEP 0440-compliant version (e.g., `3.14-rc5`)
      to be compared against the current version of this module.

    This function may also be used to test multiple versions and/or extras.  To
    do so, a string formatted ala the `pkg_resources.Requirements.parse()`
    class method (e.g., `idontevenknow<1.6,>1.9,!=1.9.6,<2.0a0,==2.4c1`) is
    passed as the `requirements` parameter. (See URL below.)

    Implementation
    ----------
    This function behaves as follows:

    * If one or more `setuptools` distributions exist for this module, this
      module was installed via either `easy_install` or `pip`. In either case,
      `setuptools` machinery is used to validate the passed requirements.
    * Else, these requirements are manually validated. Since manually
      validating extras is non-trivial, only versions are manually validated:
      * If these requirements test only extras (e.g., `Norf [foo, bar]`),
        `True` is unconditionally returned.
      * Else, these requirements test one or more versions. Then:
        1. These requirements are converted into an instance of
           `pkg_resources.Requirements`, thus parsing these requirements into
           their constituent components. This is surprisingly non-trivial!
        1. The current version of the desired module is found as follows:
           * If the passed `version` parameter is non-`None`, that is used.
           * Else, a subprocess importing this module is spawned and the value
             of this module's version attribute in that subprocess is used. The
             name of this attribute defaults to `__version__` but may be
             configured with the passed `version_attr` parameter.
        1. These requirements are validated against this version.

    Note that `setuptools` is generally considered to be the most robust means
    of comparing version strings in Python. The alternative `LooseVersion()`
    and `StrictVersion()` functions provided by the standard
    `distutils.version` module fail for common edge cases: e.g.,

        >>> from distutils.version import LooseVersion
        >>> LooseVersion('1.5') >= LooseVersion('1.5-rc2')
        False
        >>> from pkg_resources import parse_version
        >>> parse_version('1.5') >= parse_version('1.5-rc2')
        True

    Parameters
    ----------
    requirements : str
        Requirements in `pkg_resources.Requirements.parse()` format.
    version : str
        Optional PEP 0440-compliant version (e.g., `3.14-rc5`) to be used
        _instead_ of the current version of this module. If non-`None`, this
        function ignores all `setuptools` distributions for this module and
        instead compares this version against the version embedded in the
        passed requirements. This ignores the module name embedded in the
        passed requirements, permitting arbitrary versions to be compared in a
        robust manner. (See examples below.)
    version_attr : str
        Optional name of the version attribute defined by this module,
        defaulting to `__version__`. If a `setuptools` distribution exists for
        this module (there usually does) _and_ the `version` parameter is
        `None` (it usually is), this parameter is ignored.

    Returns
    ----------
    bool
        Boolean result of the desired validation.

    Raises
    ----------
    AttributeError
        If no `setuptools` distribution exists for this module _and_ this
        module defines no attribute whose name is the passed
        `version_attr` parameter.
    ValueError
        If the passed specification does _not_ comply with
        `pkg_resources.Requirements` syntax.

    See Also
    ----------
    https://pythonhosted.org/setuptools/pkg_resources.html#id12
        `pkg_resources.Requirements` syntax details.

    Examples
    ----------
        # Assume PIL 2.9.0, Sphinx 1.3.1, and SQLAlchemy 0.6 are all installed.
        >>> from PyInstaller.utils.hooks import is_module_satisfies
        >>> is_module_satisfies('sphinx >= 1.3.1')
        True
        >>> is_module_satisfies('sqlalchemy != 0.6')
        False

        # Compare two arbitrary versions. In this case, the module name
        # "sqlalchemy" is simply ignored.
        >>> is_module_satisfies('sqlalchemy != 0.6', version='0.5')
        True

        # Since the "pillow" project providing PIL publishes its version via
        # the custom "PILLOW_VERSION" attribute (rather than the standard
        # "__version__" attribute), an attribute name is passed as a fallback
        # to validate PIL when not installed by setuptools. As PIL is usually
        # installed by setuptools, this optional parameter is usually ignored.
        >>> is_module_satisfies('PIL == 2.9.0', version_attr='PILLOW_VERSION')
        True
    """
    # If no version was explicitly passed...
    if version is None:
        # If a setuptools distribution exists for this module, this validation
        # is a simple one-liner. This approach supports non-version validation
        # (e.g., of "["- and "]"-delimited extras) and is hence preferable.
        try:
            pkg_resources.get_distribution(requirements)
        # If no such distribution exists, fallback to the logic below.
        except pkg_resources.DistributionNotFound:
            pass
        # If all existing distributions violate these requirements, fail.
        except (pkg_resources.UnknownExtra, pkg_resources.VersionConflict):
            return False
        # Else, an existing distribution satisfies these requirements. Win!
        else:
            return True

    # Either a module version was explicitly passed or no setuptools
    # distribution exists for this module. First, parse a setuptools
    # "Requirements" object from this requirements string.
    requirements_parsed = pkg_resources.Requirement.parse(requirements)

    # If no version was explicitly passed, query this module for it.
    if version is None:
        module_name = requirements_parsed.project_name
        version = get_module_attribute(module_name, version_attr)

    if not version:
        # Module does not exist in the system.
        return False
    else:
        # Compare this version against the one parsed from the requirements.
        return version in requirements_parsed


def is_package(module_name):
    """
    Check if a Python module is really a module or is a package containing
    other modules.

    :param module_name: Module name to check.
    :return: True if module is a package else otherwise.
    """
    # This way determines if module is a package without importing the module.
    try:
        loader = pkgutil.find_loader(module_name)
    except Exception:
        # When it fails to find a module loader then it points probably to a class
        # or function and module is not a package. Just return False.
        return False
    else:
        if loader:
            # A package must have a __path__ attribute.
            return loader.is_package(module_name)
        else:
            # In case of None - modules is probably not a package.
            return False


def get_package_paths(package):
    """
    Given a package, return the path to packages stored on this machine
    and also returns the path to this particular package. For example,
    if pkg.subpkg lives in /abs/path/to/python/libs, then this function
    returns (/abs/path/to/python/libs,
             /abs/path/to/python/libs/pkg/subpkg).
    """
    file_attr = get_module_file_attribute(package)

    # package.__file__ = /abs/path/to/package/subpackage/__init__.py.
    # Search for Python files in /abs/path/to/package/subpackage; pkg_dir
    # stores this path.
    pkg_dir = os.path.dirname(file_attr)
    # When found, remove /abs/path/to/ from the filename; pkg_base stores
    # this path to be removed.
    pkg_base = remove_suffix(pkg_dir, package.replace('.', os.sep))

    return pkg_base, pkg_dir


def collect_submodules(package, filter=lambda name: True):
    """
    :param package: A string which names the package which will be search for
        submodules.
    :param approve: A function to filter through the submodules found,
        selecting which should be included in the returned list. It takes one
        argument, a string, which gives the name of a submodule. Only if the
        function returns true is the given submodule is added to the list of
        returned modules. For example, ``filter=lambda name: 'test' not in
        name`` will return modules that don't contain the word ``test``.
    :return: A list of strings which specify all the modules in package. Its
        results can be directly assigned to ``hiddenimports`` in a hook script;
        see, for example, ``hook-sphinx.py``.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    # Accept only strings as packages.
    if not isinstance(package, string_types):
        raise TypeError('package must be a str')

    logger.debug('Collecting submodules for %s' % package)
    # Skip a module which is not a package.
    if not is_package(package):
        logger.debug('collect_submodules - Module %s is not a package.' % package)
        return []

    # Determine the filesystem path to the specified package.
    pkg_base, pkg_dir = get_package_paths(package)

    # Walk the package. Since this performs imports, do it in a separate
    # process. Because module import may result in exta output to stdout,
    # we enclose the output module names with special prefix and suffix.
    names = exec_statement("""
        import sys
        import pkgutil
        import traceback

        # ``pkgutil.walk_packages`` doesn't walk subpackages of zipped files
        # per https://bugs.python.org/issue14209. This is a workaround.
        def walk_packages(path=None, prefix='', onerror=None):
            def seen(p, m={{}}):
                if p in m:
                    return True
                m[p] = True

            for importer, name, ispkg in pkgutil.iter_modules(path, prefix):
                if not name.startswith(prefix):   ## Added
                    name = prefix + name          ## Added
                yield importer, name, ispkg

                if ispkg:
                    try:
                        __import__(name)
                    except ImportError:
                        if onerror is not None:
                            onerror(name)
                    except Exception:
                        if onerror is not None:
                            onerror(name)
                        else:
                            traceback.print_exc(file=sys.stderr)
                            print("collect_submodules: failed to import %r!" %
                                  name, file=sys.stderr)
                    else:
                        path = getattr(sys.modules[name], '__path__', None) or []

                        # don't traverse path items we've seen before
                        path = [p for p in path if not seen(p)]

                        ## Use Py2 code here. It still works in Py3.
                        for item in walk_packages(path, name+'.', onerror):
                            yield item
                        ## This is the original Py3 code.
                        #yield from walk_packages(path, name+'.', onerror)

        for module_loader, name, ispkg in walk_packages([{}], '{}.'):
            print('\\n$_pyi:' + name + '*')
        """.format(
                  # Use repr to escape Windows backslashes.
                  repr(pkg_dir), package))

    # Include the package itself in the results.
    mods = {package}
    # Filter through the returend submodules.
    for name in names.split():
        # Filter out extra output during module imports by checking
        # for the special prefix and suffix
        if name.startswith("$_pyi:") and name.endswith("*"):
            name = name[6:-1]
        else:
            continue

        if filter(name):
            mods.add(name)

    logger.debug("collect_submodules - Found submodules: %s", mods)
    return list(mods)


def is_module_or_submodule(name, mod_or_submod):
    """
    This helper function is designed for use in the ``filter`` argument of
    ``collect_submodules``, by returning ``True`` if the given ``name`` is
    a module or a submodule of ``mod_or_submod``. For example:
    ``collect_submodules('foo', lambda name: not is_module_or_submodule(name,
    'foo.test'))`` excludes ``foo.test`` and ``foo.test.one`` but not
    ``foo.testifier``.
    """
    return name.startswith(mod_or_submod + '.') or name == mod_or_submod


# Patterns of dynamic library filenames that might be bundled with some
# installed Python packages.
PY_DYLIB_PATTERNS = [
    '*.dll',
    '*.dylib',
    'lib*.so',
]


def collect_dynamic_libs(package, destdir=None):
    """
    This routine produces a list of (source, dest) of dynamic library
    files which reside in package. Its results can be directly assigned to
    ``binaries`` in a hook script. The package parameter must be a string which
    names the package.

    :param destdir: Relative path to ./dist/APPNAME where the libraries
                    should be put.
    """
    # Accept only strings as packages.
    if not isinstance(package, string_types):
        raise TypeError('package must be a str')

    logger.debug('Collecting dynamic libraries for %s' % package)
    pkg_base, pkg_dir = get_package_paths(package)
    # Walk through all file in the given package, looking for dynamic libraries.
    dylibs = []
    for dirpath, _, __ in os.walk(pkg_dir):
        # Try all file patterns in a given directory.
        for pattern in PY_DYLIB_PATTERNS:
            files = glob.glob(os.path.join(dirpath, pattern))
            for source in files:
                # Produce the tuple
                # (/abs/path/to/source/mod/submod/file.pyd,
                #  mod/submod/file.pyd)
                if destdir:
                    # Libraries will be put in the same directory.
                    dest = destdir
                else:
                    # The directory hierarchy is preserved as in the original package.
                    dest = remove_prefix(dirpath, os.path.dirname(pkg_base) + os.sep)
                logger.debug(' %s, %s' % (source, dest))
                dylibs.append((source, dest))
    return dylibs


def collect_data_files(package, include_py_files=False, subdir=None,
                       excludes=None, includes=None):
    r"""
    This routine produces a list of ``(source, dest)`` non-Python (i.e. data)
    files which reside in ``package``. Its results can be directly assigned to
    ``datas`` in a hook script; see, for example, ``hook-sphinx.py``.
    Parameters:

    -   The ``package`` parameter is a string which names the package.
    -   By default, all Python executable files (those ending in ``.py``,
        ``.pyc``, and so on) will NOT be collected; setting the
        ``include_py_files`` argument to ``True`` collects these files as well.
        This is typically used with Python routines (such as those in
        ``pkgutil``) that search a given directory for Python executable files
        then load them as extensions or plugins.
    -   The ``subdir`` argument gives a subdirectory relative to ``package`` to
        search, which is helpful when submodules are imported at run-time from a
        directory lacking ``__init__.py``.
    -   The ``excludes`` argument contains a sequence of strings or Paths. These
        provide a list of `globs <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_
        to exclude from the collected data files; if a directory matches the
        provided glob, all files it contains will be excluded as well. All
        elements must be relative paths, which are relative to the provided
        package's path (/ ``subdir`` if provided).

        Therefore, ``*.txt`` will exclude only ``.txt`` files in ``package``\ 's
        path, while ``**/*.txt`` will exclude all ``.txt`` files in
        ``package``\ 's path and all its subdirectories. Likewise,
        ``**/__pycache__`` will exclude all files contained in any subdirectory
        named ``__pycache__``.
    -   The ``includes`` function like ``excludes``, but only include matching
        paths. ``excludes`` override ``includes``: a file or directory in both
        lists will be excluded.

    This function does not work on zipped Python eggs.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    logger.debug('Collecting data files for %s' % package)

    # Accept only strings as packages.
    if not isinstance(package, string_types):
        raise TypeError('package must be a str')

    # Compute the root path for the provided patckage.
    pkg_base, pkg_dir = get_package_paths(package)
    if subdir:
        pkg_dir = os.path.join(pkg_dir, subdir)
    pkg_base = os.path.dirname(pkg_base)
    # Ensure `pkg_base` ends with a single slash
    # Subtle difference on Windows: In some cases `dirname` keeps the
    # trailing slash, e.g. dirname("//aaa/bbb/"), see issue #4707.
    if not pkg_base.endswith(os.sep):
        pkg_base += os.sep

    # Make sure the excludes are a list; this also makes a copy, so we don't
    # modify the original.
    excludes = list(excludes) if excludes else []
    # These excludes may contain direcories which need to be searched.
    excludes_len = len(excludes)
    # Including py files means don't exclude them. This pattern will search any
    # directories for containing files, so don't modify ``excludes_len``.
    if not include_py_files:
        excludes += ['**/*' + s for s in ALL_SUFFIXES]

    # Exclude .pyo files if include_py_files is False.
    if not include_py_files and ".pyo" not in ALL_SUFFIXES:
        excludes.append('**/*.pyo')

    # If not specified, include all files. Follow the same process as the
    # excludes.
    includes = list(includes) if includes else ["**/*"]
    includes_len = len(includes)

    # Determine what source files to use.
    sources = set()

    # A helper function to glob the in/ex "cludes", adding a wildcard to refer
    # to all files under a subdirectory if a subdirectory is matched by the
    # first ``clude_len`` patterns. Otherwise, it in/excludes the matched file.
    # **This modifies** ``cludes``.
    def clude_walker(
        # A list of paths relative to ``pkg_dir`` to in/exclude.
        cludes,
        # The number of ``cludes`` for which matching directories should be
        # searched for all files under them.
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
    clude_walker(includes, includes_len, True)
    clude_walker(excludes, excludes_len, False)

    # Tranform the sources into tuples for ``datas``.
    datas = [(str(s), remove_prefix(str(s.parent), pkg_base)) for s in sources]

    logger.debug("collect_data_files - Found files: %s", datas)
    return datas


def collect_system_data_files(path, destdir=None, include_py_files=False):
    """
    This routine produces a list of (source, dest) non-Python (i.e. data)
    files which reside somewhere on the system. Its results can be directly
    assigned to ``datas`` in a hook script.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    # Accept only strings as paths.
    if not isinstance(path, string_types):
        raise TypeError('path must be a str')
    # The call to ``remove_prefix`` below assumes a path separate of ``os.sep``,
    # which may not be true on Windows; Windows allows Linux path separators in
    # filenames. Fix this by normalizing the path.
    path = os.path.normpath(path)
    # Ensure `path` ends with a single slash
    # Subtle difference on Windows: In some cases `dirname` keeps the
    # trailing slash, e.g. dirname("//aaa/bbb/"), see issue #4707.
    if not path.endswith(os.sep):
        path += os.sep

    # Walk through all file in the given package, looking for data files.
    datas = []
    for dirpath, dirnames, files in os.walk(path):
        for f in files:
            extension = os.path.splitext(f)[1]
            if include_py_files or (extension not in PY_IGNORE_EXTENSIONS):
                # Produce the tuple
                # (/abs/path/to/source/mod/submod/file.dat,
                #  mod/submod/destdir)
                source = os.path.join(dirpath, f)
                dest = remove_prefix(dirpath, path)
                if destdir is not None:
                    dest = os.path.join(destdir, dest)
                datas.append((source, dest))

    return datas


def _find_prefix(filename):
    """
    In virtualenv, _CONFIG_H and _MAKEFILE may have same or different
    prefixes, depending on the version of virtualenv.
    Try to find the correct one, which is assumed to be the longest one.
    """
    if not is_venv:
        return sys.prefix
    filename = os.path.abspath(filename)
    prefixes = [os.path.abspath(sys.prefix), base_prefix]
    possible_prefixes = []
    for prefix in prefixes:
        common = os.path.commonprefix([prefix, filename])
        if common == prefix:
            possible_prefixes.append(prefix)
    if not possible_prefixes:
        # no matching prefix, assume running from build directory
        possible_prefixes = [os.path.dirname(filename)]
    possible_prefixes.sort(key=lambda p: len(p), reverse=True)
    return possible_prefixes[0]


def relpath_to_config_or_make(filename):
    """
    The following is refactored out of hook-sysconfig and hook-distutils,
    both of which need to generate "datas" tuples for pyconfig.h and
    Makefile, under the same conditions.
    """

    # Relative path in the dist directory.
    prefix = _find_prefix(filename)
    return os.path.relpath(os.path.dirname(filename), prefix)


def copy_metadata(package_name):
    """
    This function returns a list to be assigned to the ``datas`` global
    variable. This list instructs PyInstaller to copy the metadata for the
    given package to PyInstaller's data directory.

    Parameters
    ----------
    package_name : str
        Specifies the name of the package for which metadata should be copied.

    Returns
    ----------
    list
        This should be assigned to ``datas``.

    Examples
    ----------
        >>> from PyInstaller.utils.hooks import copy_metadata
        >>> copy_metadata('sphinx')
        [('c:\\python27\\lib\\site-packages\\Sphinx-1.3.2.dist-info',
          'Sphinx-1.3.2.dist-info')]
    """

    # Some notes: to look at the metadata locations for all installed
    # packages::
    #
    #     for key, value in pkg_resources.working_set.by_key.iteritems():
    #         print('{}: {}'.format(key, value.egg_info))
    #
    # Looking at this output, I see three general types of packages:
    #
    # 1. ``pypubsub: c:\python27\lib\site-packages\pypubsub-3.3.0-py2.7.egg\EGG-INFO``
    # 2. ``codechat: c:\users\bjones\documents\documentation\CodeChat.egg-info``
    # 3. ``zest.releaser: c:\python27\lib\site-packages\zest.releaser-6.2.dist-info``
    # 4. ``pyserial: None``
    #
    # The first item shows that some metadata will be nested inside an egg. I
    # assume we'll have to deal with zipped eggs, but I don't have any examples
    # handy. The second and third items show different naming conventions for
    # the metadata-containing directory. The fourth item shows a package with no
    # metadata.
    #
    # So, in cases 1-3, copy the metadata directory. In case 4, emit an error
    # -- there's no metadata to copy.
    # See https://pythonhosted.org/setuptools/pkg_resources.html#getting-or-creating-distributions.
    # Unfortunately, there's no documentation on the ``egg_info`` attribute; it
    # was found through trial and error.
    dist = pkg_resources.get_distribution(package_name)
    metadata_dir = dist.egg_info
    # Determine a destination directory based on the standardized egg name for
    # this distribution. This avoids some problems discussed in
    # https://github.com/pyinstaller/pyinstaller/issues/1888.
    dest_dir = '{}.egg-info'.format(dist.egg_name())
    # Per https://github.com/pyinstaller/pyinstaller/issues/1888, ``egg_info``
    # isn't always defined. Try a workaround based on a suggestion by
    # @benoit-pierre in that issue.
    if metadata_dir is None:
        # We assume that this is an egg, so guess a name based on `egg_name()
        # <https://pythonhosted.org/setuptools/pkg_resources.html#distribution-methods>`_.
        metadata_dir = os.path.join(dist.location, dest_dir)

    assert os.path.exists(metadata_dir)
    logger.debug('Package {} metadata found in {} belongs in {}'.format(
      package_name, metadata_dir, dest_dir))

    return [(metadata_dir, dest_dir)]


def get_installer(module):
    """
    Try to find which package manager installed a module.

    :param module: Module to check
    :return: Package manager or None
    """
    file_name = get_module_file_attribute(module)
    site_dir = file_name[:file_name.index('site-packages') + len('site-packages')]
    # This is necessary for situations where the project name and module name don't match, i.e.
    # Project name: pyenchant Module name: enchant
    pkgs = pkg_resources.find_distributions(site_dir)
    package = None
    for pkg in pkgs:
        if module.lower() in pkg.key:
            package = pkg
            break
    metadata_dir, dest_dir = copy_metadata(package)[0]
    # Check for an INSTALLER file in the metedata_dir and return the first line
    # which should be the program that installed the module.
    installer_file = os.path.join(metadata_dir, 'INSTALLER')
    if os.path.isdir(metadata_dir) and os.path.exists(installer_file):
        with open_file(installer_file, 'r') as installer_file_object:
            lines = installer_file_object.readlines()
            if lines[0] != '':
                installer = lines[0].rstrip('\r\n')
                logger.debug(
                    'Found installer: \'{0}\' for module: \'{1}\' from package: \'{2}\''.format(installer, module,
                                                                                                package))
                return installer
    if is_darwin:
        try:
            output = exec_command_stdout('port', 'provides', file_name)
            if 'is provided by' in output:
                logger.debug(
                    'Found installer: \'macports\' for module: \'{0}\' from package: \'{1}\''.format(module, package))
                return 'macports'
        except ExecCommandFailed:
            pass
        real_path = os.path.realpath(file_name)
        if 'Cellar' in real_path:
            logger.debug(
                'Found installer: \'homebrew\' for module: \'{0}\' from package: \'{1}\''.format(module, package))
            return 'homebrew'
    return None


# ``_map_distribution_to_packages`` is expensive. Compute it when used, then
# return the memoized value. This is a simple alternative to
# ``functools.lru_cache``.
def _memoize(f):
    memo = []

    def helper():
        if not memo:
            memo.append(f())
        return memo[0]

    return helper


# Walk through every package, determining which distribution it is in.
@_memoize
def _map_distribution_to_packages():
    logger.info('Determining a mapping of distributions to packages...')
    dist_to_packages = {}
    for p in sys.path:
        # The path entry ``''`` refers to the current directory.
        if not p:
            p = '.'
        # Ignore any entries in ``sys.path`` that don't exist.
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


# Given a ``package_name`` as a string, this function returns a list of packages
# needed to satisfy the requirements. This output can be assigned directly to
# ``hiddenimports``.
def requirements_for_package(package_name):
    hiddenimports = []

    dist_to_packages = _map_distribution_to_packages()
    for requirement in pkg_resources.get_distribution(package_name).requires():
        if requirement.key in dist_to_packages:
            required_packages = dist_to_packages[requirement.key]
            hiddenimports.extend(required_packages)
        else:
            logger.warning('Unable to find package for requirement %s from '
                           'package %s.',
                           requirement.project_name, package_name)

    logger.info('Packages required by %s:\n%s', package_name, hiddenimports)
    return hiddenimports


# Given a package name as a string, return a tuple of ``datas, binaries,
# hiddenimports`` containing all data files, binaries, and modules in the given
# package. The value of ``include_py_files`` is passed directly to
# ``collect_data_files``.
#
# Typical use: ``datas, binaries, hiddenimports = collect_all('my_module_name')``.
def collect_all(
        package_name, include_py_files=True, filter_submodules=None,
        exclude_datas=None, include_datas=None):
    datas = []
    try:
        datas += copy_metadata(package_name)
    except Exception as e:
        logger.warning('Unable to copy metadata for %s: %s', package_name, e)
    datas += collect_data_files(package_name, include_py_files,
                                excludes=exclude_datas, includes=include_datas)
    binaries = collect_dynamic_libs(package_name)
    if filter_submodules:
        hiddenimports = collect_submodules(package_name,
                                           filter=filter_submodules)
    else:
        hiddenimports = collect_submodules(package_name)
    try:
        hiddenimports += requirements_for_package(package_name)
    except Exception as e:
        logger.warning('Unable to determine requirements for %s: %s',
                       package_name, e)

    return datas, binaries, hiddenimports


if is_pure_conda:
    from . import conda as conda_support  # noqa: F401
elif is_conda:
    from .conda import CONDA_META_DIR as _tmp
    logger.warning(
        "Assuming this isn't an Anaconda environment or an additional venv/"
        "pipenv/... environment manager is being used on top because the "
        "conda-meta folder %s doesn't exist.", _tmp)
    del _tmp


# These imports need to be here due to these modules recursively importing this module.
from .django import *
from .gi import *
from .qt import *
from .win32 import *
