.. _when things go wrong:

When Things Go Wrong
====================

The information above covers most normal uses of |PyInstaller|.
However, the variations of Python and third-party libraries are
endless and unpredictable.
It may happen that when you attempt to bundle your app either
|PyInstaller| itself, or your bundled app, terminates with a Python traceback.
Then please consider the following actions in sequence, before
asking for technical help.


.. _recipes and examples for specific problems:

Recipes and Examples for Specific Problems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The |PyInstaller| `FAQ`_ page has work-arounds for some common problems.
Code examples for some advanced uses and some common
problems are available on our `PyInstaller Recipes`_ page.
Some of the recipes there include:

* A more sophisticated way of collecting data files
  than the one shown above (:ref:`Adding Files to the Bundle`).

* Bundling a typical Django app.

* A use of a run-time hook to set the PyQt5 API level.

* A workaround for a multiprocessing constraint under Windows.

and others.
Many of these Recipes were contributed by users.
Please feel free to contribute more recipes!


.. _finding out what went wrong:

Finding out What Went Wrong
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Build-time Messages
--------------------

When the ``Analysis`` step runs, it produces error and warning messages.
These display after the command line if the :option:`--log-level` option allows it.
Analysis also puts messages in a warnings file
named :file:`build/{name}/warn-{name}.txt` in the
``work-path=`` directory.

Analysis creates a message when it detects an import
and the module it names cannot be found.
A message may also be produced when a class or function is declared in
a package (an ``__init__.py`` module), and the import specifies
``package.name``. In this case, the analysis can't tell if name is supposed to
refer to a submodule or package.

The "module not found" messages are not classed as errors because
typically there are many of them.
For example, many standard modules
conditionally import modules for different platforms that may or may
not be present.

All "module not found" messages are written to the
:file:`build/{name}/warn-{name}.txt` file.
They are not displayed to standard output because there are many of them.
Examine the warning file; often there will be dozens of modules not found,
but their absence has no effect.

When you run the bundled app and it terminates with an ImportError,
that is the time to examine the warning file.
Then see :ref:`Helping PyInstaller Find Modules` below for how to proceed.


Build-Time Dependency Graph
----------------------------

On each run |PyInstaller| writes a cross-referencing file about dependencies
into the build folder:
:file:`build/{name}/xref-{name}.html` in the
``work-path=`` directory is an HTML file that lists the full
contents of the import graph, showing which modules are imported
by which ones.
You can open it in any web browser.
Find a module name, then keep clicking the "imported by" links
until you find the top-level import that causes that module to be included.

If you specify :option:`--log-level=DEBUG <--log-level>` to the ``pyinstaller`` command,
|PyInstaller| additionally generates a GraphViz_ input file representing the
dependency graph.
The file is :file:`build/{name}/graph-{name}.dot` in the
``work-path=`` directory.
You can process it with any GraphViz_ command, e.g. :program:`dot`,
to produce
a graphical display of the import dependencies.

These files are very large because even the simplest "hello world"
Python program ends up including a large number of standard modules.
For this reason the graph file is not very useful in this release.



Build-Time Python Errors
-------------------------

|PyInstaller| sometimes terminates by raising a Python exception.
In most cases the reason is clear from the exception message,
for example "Your system is not supported", or "Pyinstaller
requires at least Python 3.6".
Others clearly indicate a bug that should be reported.

One of these errors can be puzzling, however:
``IOError("Python library not found!")``
|PyInstaller| needs to bundle the Python library, which is the
main part of the Python interpreter, linked as a dynamic load library.
The name and location of this file varies depending on the platform in use.
Some Python installations do not include a dynamic Python library
by default (a static-linked one may be present but cannot be used).
You may need to install a development package of some kind.
Or, the library may exist but is not in a folder where |PyInstaller|
is searching.

The places where |PyInstaller| looks for the python library are
different in different operating systems, but ``/lib`` and ``/usr/lib``
are checked in most systems.
If you cannot put the python library there,
try setting the correct path in the environment variable
``LD_LIBRARY_PATH`` in GNU/Linux or
``DYLD_LIBRARY_PATH`` in OS X.


Getting Debug Messages
----------------------

The :option:`--debug=all <--debug>` option (and its :ref:`choices <What To
Generate>`) provides a significant amount of diagnostic information.
This can be useful during development of a complex package,
or when your app doesn't seem to be starting,
or just to learn how the runtime works.

Normally the debug progress messages go to standard output.
If the :option:`--windowed` option is used when bundling a Windows app,
they are sent to any attached debugger. If you are not using a debugger
(or don't have one), the DebugView_ the free (beer) tool can be used to
display such messages. It has to be started before running the bundled
application.

.. _DebugView: https://docs.microsoft.com/en-us/sysinternals/downloads/debugview

For a :option:`--windowed` Mac OS app they are not displayed.

Consider bundling without :option:`--debug` for your production version.
Debugging messages require system calls and have an impact on performance.


.. _getting python's verbose imports:

Getting Python's Verbose Imports
--------------------------------

You can build the app with the :option:`--debug=imports<--debug>` option
(see `Getting Debug Messages`_ above),
which will pass the :option:`-v` (verbose imports) flag
to the embedded Python interpreter.
This can be extremely useful.
It can be informative even with apps that are apparently working,
to make sure that they are getting all imports from the bundle,
and not leaking out to the local installed Python.

Python verbose and warning messages always go to standard output
and are not visible when the :option:`--windowed` option is used.
Remember to not use this for your production version.


Figuring Out Why Your GUI Application Won't Start
---------------------------------------------------

If you are using the :option:`--windowed` option,
your bundled application may fail to start with an error message like
``Failed to execute script my_gui``.
In this case, you will want to get more verbose output to find out
what is going on.

* For Mac OS, you can run your application on the command line,
  i.e.``./dist/my_gui``
  in `Terminal` instead of clicking on ``my_gui.app``.

* For Windows, you will need to re-bundle your application without the
  :option:`--windowed` option.
  Then you can run the resulting executable from the command line,
  i.e.: ``my_gui.exe``.

* For Unix and GNU/Linux there in no :option:`--windowed` option.
  Anyway, if a your GUI application fails,
  you can run your application on the command line,
  i.e. ``./dist/my_gui``.
  
This should give you the relevant error that is preventing your
application from initializing, and you can then move on to other
debugging steps.


Operation not permitted error
-----------------------------

If you use the --onefile and it fails to run you program with error like::

    ./hello: error while loading shared libraries: libz.so.1: 
    failed to map segment from shared object: Operation not permitted

This can be caused by wrong permissions for the /tmp directory
(e.g. the filesystem is mounted with ``noexec`` flags).

A simple way to solve this issue is to set,
in the environment variable TMPDIR,
a path to a directory in a filesystem mounted without ``noexec`` flags, e.g.::

    export TMPDIR=/var/tmp/

.. _helping pyinstaller find modules:

Helping PyInstaller Find Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extending the Path
------------------

If Analysis recognizes that a module is needed, but cannot find that module,
it is often because the script is manipulating :data:`sys.path`.
The easiest thing to do in this case is to use the :option:`--paths` option
to list all the other places that the script might be searching for imports::

       pyi-makespec --paths=/path/to/thisdir \
                    --paths=/path/to/otherdir myscript.py

These paths will be noted in the spec file in the ``pathex`` argument.
They will be added to the current :data:`sys.path` during analysis.


Listing Hidden Imports
----------------------

If Analysis thinks it has found all the imports,
but the app fails with an import error,
the problem is a hidden import; that is, an import that is not
visible to the analysis phase.

Hidden imports can occur when the code is using :func:`__import__`,
:func:`importlib.import_module`
or perhaps :func:`exec` or :func:`eval`.
Hidden imports can also occur when an extension module uses the
Python/C API to do an import.
When this occurs, Analysis can detect nothing.
There will be no warnings, only an ImportError at run-time.

To find these hidden imports,
build the app with the :option:`--debug=imports<--debug>` flag
(see :ref:`Getting Python's Verbose Imports` above)
and run it.

Once you know what modules are needed, you add the needed modules
to the bundle using the :option:`--hidden-import` command option,
or by editing the spec file,
or with a hook file (see :ref:`Understanding PyInstaller Hooks` below).


Extending a Package's :attr:`__path__`
----------------------------------------------

Python allows a script to extend the search path used for imports
through the :attr:`__path__` mechanism.
Normally, the :attr:`__path__` of an imported module has only one entry,
the directory in which the ``__init__.py`` was found.
But ``__init__.py`` is free to extend its :attr:`__path__` to include other directories.
For example, the ``win32com.shell.shell`` module actually resolves to
``win32com/win32comext/shell/shell.pyd``.
This is because ``win32com/__init__.py`` appends ``../win32comext`` to its :attr:`__path__`.

Because the ``__init__.py`` of an imported module
is not actually executed during analysis,
changes it makes to :attr:`__path__` are not seen by |PyInstaller|.
We fix the problem with the same hook mechanism we use for hidden imports,
with some additional logic; see :ref:`Understanding PyInstaller Hooks` below.

Note that manipulations of ``__path__`` hooked in this way apply only
to the Analysis.
At runtime all imports are intercepted and satisfied from within the
bundle. ``win32com.shell`` is resolved the same
way as ``win32com.anythingelse``, and ``win32com.__path__``
knows nothing of ``../win32comext``.

Once in a while, that's not enough.


.. _changing runtime behavior:

Changing Runtime Behavior
-------------------------

More bizarre situations can be accomodated with runtime hooks.
These are small scripts that manipulate the environment before your main script runs,
effectively providing additional top-level code to your script.

There are two ways of providing runtime hooks.
You can name them with the option :option:`--runtime-hook`\ =\ *path-to-script*.

Second, some runtime hooks are provided.
At the end of an analysis,
the names in the module list produced by the Analysis phase are looked up in
:file:`loader/rthooks.dat` in the |PyInstaller| install folder.
This text file is the string representation of a
Python dictionary. The key is the module name, and the value is a list
of hook-script pathnames.
If there is a match, those scripts are included in the bundled app
and will be called before your main script starts.

Hooks you name with the option are executed
in the order given, and before any installed runtime hooks.
If you specify  :option:`--runtime-hook=file1.py --runtime-hook=file2.py
<--runtime-hook>` then the execution order at runtime will be:

1. Code of :file:`file1.py`.
2. Code of :file:`file2.py`.
3. Any hook specified for an included module that is found
   in :file:`rthooks/rthooks.dat`.
4. Your main script.

Hooks called in this way, while they need to be careful of what they import,
are free to do almost anything.
One reason to write a run-time hook is to
override some functions or variables from some modules.
A good example of this is the Django runtime
hook (see ``loader/rthooks/pyi_rth_django.py`` in the
|PyInstaller| folder).
Django imports some modules dynamically and it is looking
for some ``.py`` files.
However ``.py`` files are not available in the one-file bundle.
We need to override the function
``django.core.management.find_commands``
in a way that will just return a list of values.
The runtime hook does this as follows::

    import django.core.management
    def _find_commands(_):
        return """cleanup shell runfcgi runserver""".split()
    django.core.management.find_commands = _find_commands



Getting the Latest Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have some reason to think you have found a bug in |PyInstaller|
you can try downloading the latest development version.
This version might have fixes or features that are not yet at `PyPI`_.
You can download the latest stable version and the latest development
version from the `PyInstaller Downloads`_ page.

You can also install the latest version of |PyInstaller| directly
using pip_::

    pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip

Asking for Help
~~~~~~~~~~~~~~~~~~

When none of the above suggestions help,
do ask for assistance on the `PyInstaller Email List`_.

Then, if you think it likely that you see a bug in |PyInstaller|,
refer to the `How to Report Bugs`_ page.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
