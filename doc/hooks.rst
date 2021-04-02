.. _understanding pyinstaller hooks:

Understanding PyInstaller Hooks
==================================

.. note::

   We strongly encourage package developers
   to provide hooks with their packages.
   See section :ref:`provide hooks with package` for how easy this is.

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
It can also import helper methods from :mod:`PyInstaller.utils.hooks`
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
command with the :option:`--additional-hooks-dir` option.
If the hook file(s) are at the same level as the script,
the command could be simply::

    pyinstaller --additional-hooks-dir=. myscript.py

If you write a hook for a module used by others,
please ask the package developer to
:ref:`include the hook with her/his package <provide hooks with package>`
or send us the hook file so we can make it available.


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
For example it could test :data:`sys.version` and adjust its
assignment to ``hiddenimports`` based on that.
There are many hooks in the |PyInstaller| installation,
but a much larger collection can be found in the
`community hooks package <https://github.com/pyinstaller/pyinstaller-hooks-contrib>`_.
Please browse through them for examples.

.. _provide hooks with package:

Providing PyInstaller Hooks with your Package
------------------------------------------------

As a package developer you can provide hooks for PyInstaller
within your package.
This has the major benefit
that you can easily adopt the hooks
when your package changes.
Thus your package's users don't need to wait until PyInstaller
might catch up with these changes.
If both PyInstaller and your package provide hooks for some module,
your package's hooks take precedence,
but can still be overridden by the command line option
:option:`--additional-hooks-dir`.


You can tell PyInstaller about the additional hooks
by defining some simple `setuptools entry-points
<https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins>`_
in your package.
Therefore add entries like these to your :file:`setup.cfg`::

  [options.entry_points]
  pyinstaller40 =
    hook-dirs = pyi_hooksample.__pyinstaller:get_hook_dirs
    tests     = pyi_hooksample.__pyinstaller:get_PyInstaller_tests

This defines two entry-points:

:``pyinstaller40.hook-dirs`` for hook registration:

   This entry point refers to a function
   that will be invoked with no parameters.
   It must return a sequence of strings,
   each element of which provides an additional absolute path
   to search for hooks.
   This is equivalent to passing the :option:`--additional-hooks-dir`
   command-line option to PyInstaller for each string in the sequence.

   In this example, the function is ``get_hook_dirs() -> List[str]``.

:``pyinstaller40.tests`` for test registration:

   This entry point refers to a function
   that will be invoked with no parameters.
   It must return a sequence of strings,
   each element of which provides an additional absolute path
   to a directory tree or to a Python source file.
   These paths are then passed to `pytest` for test discovery.
   This allows both testing by this package and by PyInstaller.

   In this project, the function is ``get_PyInstaller_tests() -> List[str]``.

A sample project providing a guide for
integrating PyInstaller hooks and tests into a package
is available at
https://github.com/pyinstaller/hooksample.
This project demonstrates defining a library
which includes PyInstaller hooks along with tests for those hooks
and sample file for integration into CD/CI testing.
Detailed documentation about this sample project
is available at
https://pyinstaller-sample-hook.readthedocs.io/en/latest/.


Hook Global Variables
-----------------------

A majority of the existing hooks consist entirely of assignments of
values to one or more of the following global variables.
If any of these are defined by the hook, Analysis takes their values and
applies them to the bundle being created.

``hiddenimports``
    A list of module names (relative or absolute) that should
    be part of the bundled app.
    This has the same effect as the :option:`--hidden-import` command line option,
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

        excludedimports = ['tkinter']

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
   you can use helper functions from the :mod:`PyInstaller.utils.hooks` module
   (see below) to create this list, for example::

      datas  = collect_data_files('submodule1')
      datas += collect_data_files('submodule2')

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

.. automodule:: PyInstaller.compat
.. py:currentmodule:: PyInstaller.compat

A hook may import the following names from :mod:`PyInstaller.compat`,
for example::

   from PyInstaller.compat import base_prefix, is_win

.. py:data:: is_py36, is_py37, is_py38, is_py39, is_py310

    True when the current version of Python is at least 3.6, 3.7, 3.8, 3.9,
    or 3.10, respectively.

.. py:data::  is_win

   True in a Windows system.

.. py:data:: is_cygwin

   True when ``sys.platform == 'cygwin'``.

.. py:data:: is_darwin

   True in Mac OS X.

.. py:data:: is_linux

   True in any GNU/Linux system.

.. py:data:: is_solar

   True in Solaris.

.. py:data:: is_aix

   True in AIX.

.. py:data:: is_freebsd

   True in FreeBSD.

.. py:data:: is_openbsd

   True in OpenBSD.

.. py:data:: is_venv

   True in any virtual environment (either virtualenv or venv).

.. py:data:: base_prefix

   String, the correct path to the base Python installation,
   whether the installation is native or a virtual environment.

.. py:data:: EXTENSION_SUFFIXES

   List of Python C-extension file suffixes. Used for finding all
   binary dependencies in a folder; see :file:`hook-cryptography.py`
   for an example.


Useful Items in ``PyInstaller.utils.hooks``
--------------------------------------------

.. py:currentmodule:: PyInstaller.utils.hooks

.. automodule:: PyInstaller.utils.hooks

A hook may import useful functions from :mod:`PyInstaller.utils.hooks`.
Use a fully-qualified import statement, for example::

   from PyInstaller.utils.hooks import collect_data_files, eval_statement

The functions listed here are generally useful and used in a number of existing
hooks.

.. autofunction:: exec_statement
.. autofunction:: eval_statement
.. autofunction:: is_module_satisfies
.. autofunction:: collect_all
.. autofunction:: collect_submodules
.. autofunction:: is_module_or_submodule
.. autofunction:: collect_data_files
.. autofunction:: collect_dynamic_libs
.. autofunction:: get_module_file_attribute
.. autofunction:: get_package_paths
.. autofunction:: copy_metadata
.. autofunction:: collect_entry_point
.. autofunction:: get_homebrew_path


Support for Conda
.................

.. automodule:: PyInstaller.utils.hooks.conda

.. autofunction:: PyInstaller.utils.hooks.conda.distribution

.. autofunction:: PyInstaller.utils.hooks.conda.package_distribution

.. autofunction:: PyInstaller.utils.hooks.conda.files

.. autofunction:: PyInstaller.utils.hooks.conda.requires

.. autoclass:: PyInstaller.utils.hooks.conda.Distribution

.. autoclass:: PyInstaller.utils.hooks.conda.PackagePath
    :members:

.. autofunction:: PyInstaller.utils.hooks.conda.walk_dependency_tree

.. autofunction:: PyInstaller.utils.hooks.conda.collect_dynamic_libs

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

:attr:`__path__`:
   A list of the absolute paths of all directories comprising the module
   if it is a package, or ``None``. Typically the list contains only the
   absolute path of the package's directory.

``co``:
    Code object compiled from the contents of ``__file__`` (e.g., via the
    :func:`compile` builtin).

``analysis``:
    The ``Analysis`` object that loads the hook.

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

Hooks may access the user parameters, given in the ``hooksconfig`` argument in
the spec file, by calling :func:`~PyInstaller.utils.hooks.get_hook_config`
inside a `hook()` function.

.. autofunction:: PyInstaller.utils.hooks.get_hook_config

The ``pre_find_module_path( pfmp_api )`` Method
------------------------------------------------

You may write a hook with the special function ``pre_find_module_path( pfmp_api )``.
This method is called when the hooked module name is first seen
by Analysis, before it has located the path to that module or package
(hence the name "pre-find-module-path").

Hooks of this type are only recognized if they are stored in
a sub-folder named ``pre_find_module_path`` in a hooks folder,
either in the distributed hooks folder or an :option:`--additional-hooks-dir` folder.
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
either in the distributed hooks folder or an :option:`--additional-hooks-dir` folder.
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
   :attr:`__path__` attribute.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
