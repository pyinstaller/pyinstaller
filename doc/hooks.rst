.. _understanding pyinstaller hooks:

Understanding PyInstaller Hooks
==================================

In summary, a "hook" file extends |PyInstaller| to adapt it to
the special needs and methods used by a Python package.
The word "hook" is used for two kinds of files.
A *runtime* hook helps the bootloader to launch an app.
For more on runtime hooks, see :ref:`Changing Runtime Behavior`.
Other hooks run while an app is being analyzed.
They help the Analysis phase find needed files.

The majority of Python packages use normal methods of importing
their dependencies, and |PyInstaller| locates all their files without difficulty.
But some packages make unusual uses of the Python import mechanism,
or make clever changes to the import system at runtime.
For this or other reasons, |PyInstaller| cannot reliably find
all the needed files, or may include too many files.
A hook can tell about additional source files or data files to import,
or files not to import.

A hook file is a Python script, and can use all Python features.
It can also import helper methods from ``PyInstaller.utils.hooks``
and useful variables from ``PyInstaller.compat``.
These helpers are documented below.

The name of a hook file is :file:`hook-{full.import.name}.py`,
where *full.import.name* is
the fully-qualified name of an imported script or module.
You can browse through the existing hooks in the
``hooks`` folder of the |PyInstaller| distribution folder
and see the names of the packages for which hooks have been written.
For example ``hook-PyQt5.QtCore.py`` is a hook file telling
about hidden imports needed by the module ``PyQt5.QtCore``.
When your script contains ``import PyQt5.QtCore``
(or ``from PyQt5 import QtCore``),
Analysis notes that ``hook-PyQt5.QtCore.py`` exists, and will call it.

Many hooks consist of only one statement, an assignment to ``hiddenimports``.
For example, the hook for the `dnspython`_ package, called
``hook-dns.rdata.py``, has only this statement::

    hiddenimports = [
        "dns.rdtypes.*",
        "dns.rdtypes.ANY.*"
    ]

When Analysis sees ``import dns.rdata`` or ``from dns import rdata``
it calls ``hook-dns.rdata.py`` and examines its value
of ``hiddenimports``.
As a result, it is as if your source script also contained::

    import dns.rdtypes.*
    import dsn.rdtypes.ANY.*

A hook can also cause the addition of data files,
and it can cause certain files to *not* be imported.
Examples of these actions are shown below.

When the module that needs these hidden imports is useful only to your project,
store the hook file(s) somewhere near your source file.
Then specify their location to the ``pyinstaller`` or ``pyi-makespec``
command with the ``--additional-hooks-dir=`` option.
If the hook file(s) are at the same level as the script,
the command could be simply::

    pyinstaller --additional-hooks-dir=. myscript.py

If you write a hook for a module used by others,
please send us the hook file so we can make it available.


How a Hook Is Loaded
-----------------------

A hook is a module named :file:`hook-{full.import.name}.py`
in a folder where the Analysis object looks for hooks.
Each time Analysis detects an import, it looks for a hook file with
a matching name.
When one is found, Analysis imports the hook's code into a Python namespace.
This results in the execution of all top-level statements in the hook source,
for example import statements, assignments to global names, and
function definitions.
The names defined by these statements are visible to Analysis
as attributes of the namespace.

Thus a hook is a normal Python script and can use all normal Python facilities.
For example it could test ``sys.version`` and adjust its
assignment to ``hiddenimports`` based on that.
There are over 150 hooks in the |PyInstaller| installation.
You are welcome to browse through them for examples.


Hook Global Variables
-----------------------

A majority of the existing hooks consist entirely of assignments of
values to one or more of the following global variables.
If any of these are defined by the hook, Analysis takes their values and
applies them to the bundle being created.

``hiddenimports``
    A list of module names (relative or absolute) that should
    be part of the bundled app.
    This has the same effect as the ``--hidden-import`` command line option,
    but it can contain a list of names and is applied automatically
    only when the hooked module is imported.
    Example::

        hiddenimports = ['_gdbm', 'socket', 'h5py.defs']

``excludedimports``
    A list of absolute module names that should
    *not* be part of the bundled app.
    If an excluded module is imported only by the hooked module or one
    of its sub-modules, the excluded name and its sub-modules
    will not be part of the bundle.
    (If an excluded name is explicitly imported in the
    source file or some other module, it will be kept.)
    Several hooks use this to prevent automatic inclusion of
    the ``tkinter`` module. Example::

        excludedimports = [modname_tkinter]

``datas``
   A list of files to bundle with the app as data.
   Each entry in the list is a tuple containing two strings.
   The first string specifies a file (or file "glob") in this system,
   and the second specifies the name(s) the file(s) are to have in
   the bundle.
   (This is the same format as used for the ``datas=`` argument,
   see :ref:`Adding Data Files`.)
   Example::

      datas = [ ('/usr/share/icons/education_*.png', 'icons') ]

   If you need to collect multiple directories or nested directories,
   you can use helper functions from the ``PyInstaller.utils.hooks`` module
   (see below) to create this list, for example::

      datas = collect_data_files('submodule1')
      datas+= collect_data_files('submodule2')

   In rare cases you may need to apply logic to locate
   particular files within the file system,
   for example because the files are
   in different places on different platforms or under different versions.
   Then you can write a ``hook()`` function as described
   below under :ref:`The hook(hook_api) Function`.


``binaries``
   A list of files or directories to bundle as binaries.
   The format is the same as ``datas`` (tuples with strings that
   specify the source and the destination).
   Binaries is a special case of ``datas``, in that PyInstaller will
   check each file to see if it depends on other dynamic libraries.
   Example::

      binaries = [ ('C:\\Windows\\System32\\*.dll', 'dlls') ]

   Many hooks use helpers from the ``PyInstaller.utils.hooks`` module
   to create this list (see below)::

      binaries = collect_dynamic_libs('zmq')


Useful Items in ``PyInstaller.compat``
----------------------------------------

A hook may import the following names from ``PyInstaller.compat``,
for example::

   from PyInstaller.compat import modname_tkinter, is_win

``is_py2``:
   True when the active Python is version 2.7.
``is_py3``:
   True when the active Python is version 3.X.
``is_py35``, ``is_py36``, ``is_py37``:
   True when the current version of Python is at least 3.5, 3.6, or 3.7 respectively.

``is_win``:
   True in a Windows system.
``is_cygwin``:
   True when ``sys.platform=='cygwin'``.
``is_darwin``:
   True in Mac OS X.
``is_linux``:
   True in any Linux system (``sys.platform.startswith('linux')``).
``is_solar``:
   True in Solaris.
``is_aix``:
   True in AIX.
``is_freebsd``:
   True in FreeBSD.

``is_venv``:
   True in any virtual environment (either virtualenv or venv).
``base_prefix``:
   String, the correct path to the base Python installation,
   whether the installation is native or a virtual environment.

``modname_tkinter``:
   String, ``Tkinter`` in Python 2.7 but ``tkinter`` in Python 3.
   To prevent an unnecessary import of Tkinter, write::

      from PyInstaller.compat import modname_tkinter
      excludedimports = [ modname_tkinter ]

``EXTENSION_SUFFIXES``:
   List of Python C-extension file suffixes. Used for finding all
   binary dependencies in a folder; see file:`hook-cryptography.py`
   for an example.

Useful Items in ``PyInstaller.utils.hooks``
--------------------------------------------

A hook may import useful functions from ``PyInstaller.utils.hooks``.
Use a fully-qualified import statement, for example::

   from PyInstaller.utils.hooks import collect_data_files, eval_statement

The ``PyInstaller.utils.hooks`` functions listed here are generally useful
and used in a number of existing hooks.
There are several more functions besides these that serve the needs
of specific hooks, such as hooks for PyQt4/5.
You are welcome to read the ``PyInstaller.utils.hooks`` module
(and read the existing hooks that import from it) to get code and ideas.

``exec_statement( 'statement' )``:
   Execute a single Python statement in an externally-spawned interpreter
   and return the standard output that results, as a string.
   Examples::

     tk_version = exec_statement(
        "from _tkinter import TK_VERSION; print(TK_VERSION)"
        )

     mpl_data_dir = exec_statement(
        "import matplotlib; print(matplotlib._get_data_path())"
        )
     datas = [ (mpl_data_dir, "") ]

``eval_statement( 'statement' )``:
   Execute a single Python statement in an externally-spawned interpreter.
   If the resulting standard output text is not empty, apply
   the ``eval()`` function to it; else return None. Example::

      databases = eval_statement('''
         import sqlalchemy.databases
         print(sqlalchemy.databases.__all__)
         ''')
      for db in databases:
         hiddenimports.append("sqlalchemy.databases." + db)

``is_module_satisfies( requirements, version=None, version_attr='__version__' )``:
   Check that the named module (fully-qualified) exists and satisfies the
   given requirement. Example::

       if is_module_satisfies('sqlalchemy >= 0.6'):

   This function provides robust version checking based on the same low-level
   algorithm used by ``easy_install`` and ``pip``, and should always be
   used in preference to writing your own comparison code.
   In particular, version strings should never be compared lexicographically
   (except for exact equality).
   For example ``'00.5' > '0.6'`` returns True, which is not the desired result.

   The ``requirements`` argument uses the same syntax as supported by
   the `Package resources`_ module of setup tools (follow the link to
   see the supported syntax).

   The optional ``version`` argument is is a PEP0440-compliant,
   dot-delimited version specifier such as ``'3.14-rc5'``.

   When the package being queried has been installed by ``easy_install``
   or ``pip``, the existing setup tools machinery is used to perform the test
   and the ``version`` and ``version_attr`` arguments are ignored.

   When that is not the case, the ``version`` argument is taken as the
   installed version of the package
   (perhaps obtained by interrogating the package in some other way).
   When ``version`` is ``None``, the named package is imported into a
   subprocess, and the ``__version__`` value of that import is tested.
   If the package uses some other name than ``__version__`` for its version
   global, that name can be passed as the ``version_attr`` argument.

   For more details and examples refer to the function's doc-string, found
   in ``Pyinstaller/utils/hooks/__init__.py``.


``collect_all( 'package-name', include_py_files=False )``:

   Given a package name as a string, this function returns a tuple of ``datas, binaries,
   hiddenimports`` containing all data files, binaries, and modules in the given
   package, including any modules specified in the requirements for the
   distribution of this module. The value of ``include_py_files`` is passed
   directly to ``collect_data_files``.

   Typical use: ``datas, binaries, hiddenimports = collect_all('my_module_name')``.
   For example, ``hook-gevent.py`` invokes ``collect_all``, which gathers:

   * All data files, such as ``__greenlet_primitives.pxd``, ``__hub_local.pxd``,
     and many, many more.
   * All binaries, such as ``__greenlet_primitives.cp37-win_amd64.pyd`` (on a
     Windows 64-bit install) and many, many more.
   * All modules in ``gevent``, such as ``gevent.threadpool``,
     ``gevent._semaphore``, and many, many more.
   * All requirements. ``pip show gevent`` gives ``Requires: cffi, greenlet``.
     Therefore, the ``cffi`` and ``greenlet`` modules are included.

``collect_submodules( 'package-name', pattern=None )``:
   Returns a list of strings that specify all the modules in a package,
   ready to be assigned to the ``hiddenimports`` global.
   Returns an empty list when ``package`` does not name a package
   (a package is defined as a module that contains a ``__path__`` attribute).

   The ``pattern``, if given, is function to filter through the submodules
   found, selecting which should be included in the returned list. It takes one
   argument, a string, which gives the name of a submodule. Only if the
   function returns true is the given submodule is added to the list of
   returned modules. For example, ``filter=lambda name: 'test' not in
   name`` will return modules that don't contain the word ``test``.

``is_module_or_submodule( name, mod_or_submod )``:
   This helper function is designed for use in the ``filter`` argument of
   ``collect_submodules``, by returning ``True`` if the given ``name`` is
   a module or a submodule of ``mod_or_submod``. For example:
   ``collect_submodules('foo', lambda name: not is_module_or_submodule(name,
   'foo.test'))`` excludes ``foo.test`` and ``foo.test.one`` but not
   ``foo.testifier``.

``collect_data_files( 'module-name', include_py_files=False, subdir=None )``:
   Returns a list of (source, dest) tuples for all non-Python (i.e. data)
   files found in *module-name*, ready to be assigned to the ``datas`` global.
   *module-name* is the fully-qualified name of a module or
   package (but not a zipped "egg").
   The function uses ``os.walk()`` to visit the module directory recursively.
   ``subdir``, if given, restricts the search to a relative subdirectory.

   Normally Python executable files (ending in ``.py``, ``.pyc``, etc.)
   are not collected. Pass ``include_py_files=True`` to collect those
   files as well.
   (This can be used with routines such as those in ``pkgutil`` that
   search a directory for Python executable files and load them as
   extensions or plugins.)

``collect_dynamic_libs( 'module-name' )``:
   Returns a list of (source, dest) tuples for all the dynamic libs
   present in a module directory.
   The list is ready to be assigned to the ``binaries`` global variable.
   The function uses ``os.walk()`` to examine all files in the
   module directory recursively.
   The name of each file found is tested against the likely patterns for
   a dynamic lib: ``*.dll``, ``*.dylib``, ``lib*.pyd``, and ``lib*.so``.
   Example::

      binaries = collect_dynamic_libs( 'enchant' )

``get_module_file_attribute( 'module-name' )``:
   Return the absolute path to *module-name*, a fully-qualified module name.
   Example::

      nacl_dir = os.path.dirname(get_module_file_attribute('nacl'))

``get_package_paths( 'package-name' )``:
   Given the name of a package, return a tuple.
   The first element is the absolute path to the folder where the package is stored.
   The second element is the absolute path to the named package.
   For example, if ``pkg.subpkg`` is stored in ``/abs/Python/lib``
   the result of::

      get_package_paths( 'pkg.subpkg' )

   is the tuple, ``( '/abs/Python/lib', '/abs/Python/lib/pkg/subpkg' )``

``copy_metadata( 'package-name' )``:
   Given the name of a package, return the name of its distribution
   metadata folder as a list of tuples ready to be assigned
   (or appended) to the ``datas`` global variable.

   Some packages rely on metadata files accessed through the
   ``pkg_resources`` module.
   Normally |PyInstaller| does not include these metadata files.
   If a package fails without them, you can use this
   function in a hook file to easily add them to the bundle.
   The tuples in the returned list have two strings.
   The first is the full pathname to a folder in this system.
   The second is the folder name only.
   When these tuples are added to ``datas``\ ,
   the folder will be bundled at the top level.
   If *package-name* does not have metadata, an
   AssertionError exception is raised.


``get_homebrew_path( formula='' )``:
   Return the homebrew path to the named formula, or to the
   global prefix when formula is omitted. Returns None if
   not found.


``django_find_root_dir()``:
   Return the path to the top-level Python package containing
   the Django files, or None if nothing can be found.

``django_dottedstring_imports( 'django-root-dir' )``
   Return a list of all necessary Django modules specified in
   the Django settings.py file, such as the
   ``Django.settings.INSTALLED_APPS`` list and many others.


.. _the hook(hook_api) function:

The ``hook(hook_api)`` Function
--------------------------------

In addition to, or instead of, setting global values,
a hook may define a function ``hook(hook_api)``.
A ``hook()`` function should only be needed if the hook
needs to apply sophisticated logic or to make a complex
search of the source machine.

The Analysis object calls the function and passes it a ``hook_api`` object
which has the following immutable properties:

``__name__``:
   The fully-qualified name of the module that caused the
   hook to be called, e.g., ``six.moves.tkinter``.

``__file__``:
   The absolute path of the module. If it is:

      * A standard (rather than namespace) package, this is the absolute path
        of this package's directory.

      * A namespace (rather than standard) package, this is the abstract
        placeholder ``-``.

      * A non-package module or C extension, this is the absolute path of the
        corresponding file.

``__path__``:
   A list of the absolute paths of all directories comprising the module
   if it is a package, or ``None``. Typically the list contains only the
   absolute path of the package's directory.

The ``hook_api`` object also offers the following methods:

``add_imports( *names )``:
   The ``names`` argument may be a single string or a list of strings
   giving the fully-qualified name(s) of modules to be imported.
   This has the same effect as adding the names to the ``hiddenimports`` global.

``del_imports( *names )``:
   The ``names`` argument may be a single string or a list of strings,
   giving the fully-qualified name(s) of modules that are not
   to be included if they are imported only by the hooked module.
   This has the same effect as adding names to the ``excludedimports`` global.

``add_datas( tuple_list )``:
   The ``tuple_list`` argument has the format used with the ``datas`` global
   variable. This call has the effect of adding items to that list.

``add_binaries( tuple_list )``:
   The ``tuple_list`` argument has the format used with the ``binaries``
   global variable. This call has the effect of adding items to that list.

The ``hook()`` function can add, remove or change included files using the
above methods of ``hook_api``.
Or, it can simply set values in the four global variables, because
these will be examined after ``hook()`` returns.

The ``pre_find_module_path( pfmp_api )`` Method
------------------------------------------------

You may write a hook with the special function ``pre_find_module_path( pfmp_api )``.
This method is called when the hooked module name is first seen
by Analysis, before it has located the path to that module or package
(hence the name "pre-find-module-path").

Hooks of this type are only recognized if they are stored in
a sub-folder named ``pre_find_module_path`` in a hooks folder,
either in the distributed hooks folder or an ``--additional-hooks-dir`` folder.
You may have normal hooks as well as hooks of this type for the same module.
For example |PyInstaller| includes both a ``hooks/hook-distutils.py``
and also a ``hooks/pre_find_module_path/hook-distutils.py``.

The ``pfmp_api`` object that is passed has the following immutable attribute:

``module_name``:
   A string, the fully-qualified name of the hooked module.

The ``pfmp_api`` object has one mutable attribute, ``search_dirs``.
This is a list of strings that specify the absolute path, or paths,
that will be searched for the hooked module.
The paths in the list will be searched in sequence.
The ``pre_find_module_path()`` function may replace or change
the contents of ``pfmp_api.search_dirs``.

Immediately after return from ``pre_find_module_path()``, the contents
of ``search_dirs`` will be used to find and analyze the module.

For an example of use,
see the file :file:`hooks/pre_find_module_path/hook-distutils.py`.
It uses this method to redirect a search for distutils when
|PyInstaller| is executing in a virtual environment.


The ``pre_safe_import_module( psim_api )`` Method
---------------------------------------------------

You may write a hook with the special function ``pre_safe_import_module( psim_api )``.
This method is called after the hooked module has been found,
but *before* it and everything it recursively imports is added
to the "graph" of imported modules.
Use a pre-safe-import hook in the unusual case where:

* The script imports *package.dynamic-name*
* The *package* exists
* however, no module *dynamic-name* exists at compile time (it will be defined somehow at run time)

You use this type of hook to make dynamically-generated names known to PyInstaller.
PyInstaller will not try to locate the dynamic names, fail, and report them as missing.
However, if there are normal hooks for these names, they will be called.

Hooks of this type are only recognized if they are stored in a sub-folder
named ``pre_safe_import_module`` in a hooks folder,
either in the distributed hooks folder or an ``--additional-hooks-dir`` folder.
(See the distributed ``hooks/pre_safe_import_module`` folder for examples.)

You may have normal hooks as well as hooks of this type for the same module.
For example the distributed system has both a ``hooks/hook-gi.repository.GLib.py``
and also a ``hooks/pre_safe_import_module/hook-gi.repository.GLib.py``.

The ``psim_api`` object offers the following attributes,
all of which are immutable (an attempt to change one raises an exception):

``module_basename``:
   String, the unqualified name of the hooked module, for example ``text``.

``module_name``:
   String, the fully-qualified name of the hooked module, for example
   ``email.mime.text``.

``module_graph``:
   The module graph representing all imports processed so far.

``parent_package``:
   If this module is a top-level module of its package, ``None``.
   Otherwise, the graph node that represents the import of the
   top-level module.

The last two items, ``module_graph`` and ``parent_package``,
are related to the module-graph, the internal data structure used by
|PyInstaller| to document all imports.
Normally you do not need to know about the module-graph.

The ``psim_api`` object also offers the following methods:

``add_runtime_module( fully_qualified_name )``:
   Use this method to add an imported module whose name may not
   appear in the source because it is dynamically defined at run-time.
   This is useful to make the module known to |PyInstaller| and avoid misleading warnings.
   A typical use applies the name from the ``psim_api``::

      psim_api.add_runtime_module( psim_api.module_name )

``add_alias_module( real_module_name, alias_module_name )``:
   ``real_module_name`` is the fully-qualifed name of an existing
   module, one that has been or could be imported by name
   (it will be added to the graph if it has not already been imported).
   ``alias_module_name`` is a name that might be referenced in the
   source file but should be treated as if it were ``real_module_name``.
   This method ensures that if |PyInstaller| processes an import of
   ``alias_module_name`` it will use ``real_module_name``.

``append_package_path( directory )``:
   The hook can use this method to add a package path
   to be searched by |PyInstaller|, typically an import
   path that the imported module would add dynamically to
   the path if the module was executed normally.
   ``directory`` is a string, a pathname to add to the
   ``__path__`` attribute.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
