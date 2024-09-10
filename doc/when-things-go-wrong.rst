.. _when things go wrong:

When Things Go Wrong (runtime)
==============================

This guide covers how to go about debugging a PyInstaller application and the
most common error patterns.


Things not to do
~~~~~~~~~~~~~~~~

Firstly, here are some popular go-to non-remedies that **will not fix your
problem**. (Attempt them if you must in order to get it out of your system but
don't be surprised when they accomplish nothing.)

* Reinstall random packages

* Reinstall PyInstaller

* Try with umpteen different versions of PyInstaller

* Reinstall Python (although uninstalling Anaconda in favour of a regular
  python.org installation is likely to fix DLL load issues)

* Reinstall Windows (yes, people will go to that extreme)

* Run either PyInstaller or your application as administrator/root (even if you
  get permission errors)

* Manually copy packages from ``site-packages`` into your built application

* Believe anything that ChatGPT says about PyInstaller or portable code

* Groundlessly pick one random *collect something* PyInstaller flag and apply it
  to every single module or file in your dependency tree


Meaningful diagnostics
~~~~~~~~~~~~~~~~~~~~~~

To debug with any degree of effectiveness, you need the error message. To get
it:

* On Windows, remove :option:`--windowed`/:option:`--noconsole` flags if your
  using them or, for ``.spec`` file users, ensure that the ``console`` parameter
  to ``EXE()`` is set to :data:`True`. Without a console, no error output can be
  emitted.

* Run your application from a terminal::

      ./dist/your-application/your-application.exe

  For macOS ``.app`` bundles, the equivalent command is::

      ./dist/your-application.app/Contents/MacOS/your-application

  Launching your application by double clicking on it in a file manager will
  cause your application to run in a temporary console which will disappear
  whenever an exception is raised – possibly so quickly that you won't see it at
  all (and no, we can't change this behavior – it's how the OS works, not a
  decision that PyInstaller makes).

* Optionally (but strongly recommended), switch to onedir mode so that you can
  see what's inside you application (although note that you will not be able to
  see ``.py`` files).

* Remove the :option:`--strip` option if you are using it.

* Disable any source code obfuscators if you are using one.

* Purge any *catch-all* exception handling that can hide or obfuscate bugs::

    try:
        something complicated
    except Exception as ex:
        # Don't do this. It throws away everything you need to know!
        print("An error occurred. Please try again")
        # Or this since it throws away the stacktrace
        print(f"Error: {ex}")
        sys.exit(1)
        # Likewise with this
        raise SystemExit(ex)

If you followed the above, you are most likely now looking at a Python
stacktrace indicating the type of error (usually some form of
*file/module/resource/library/symbol/routine/distribution not found error*). The
rest of this page is broken out into the various common error types and their
corresponding remedies.


Common failure patterns and their remedies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Fix a ModuleNotFoundError
-------------------------

A :class:`ModuleNotFoundError` typically occurs because PyInstaller didn't know
to collect a module **or** because it couldn't find it at build time. During a
build, PyInstaller creates an *xref* file, located at
``build/your-application/xref-your-application.html``, which lists every module
it either collected, considered collecting or failed to collect. See each
subsection below for the module's entry type (or possibly lack of entry) in the
``xref`` file.

.. note::

    Raw ``.py`` files are not packaged by PyInstaller (they're byte-complied,
    compressed and embedded directly into the EXE file) so listing the contents
    of a onedir build will not let you see which libraries were collected.


Module absent from xref file
............................

If the (sub)module isn't mentioned in the ``xref`` file at all then
PyInstaller's dependency scanner never saw any dependency on the offending
module. This is the most common failure mode in PyInstaller. Fix it by adding
:option:`--hiddenimport=offending.module` to your build command or, for spec
file users, by adding ``"offending.module"`` to the ``hiddenimports`` list.

You may find that one package has many of these issues (typically because it
contains *lazily-loaded submodules* or inordinate amounts of Cython); all
submodules of a given package can be collected using
:option:`--collect-submodules=package` or
:func:`hiddenimports=[*collect_submodules("package")]
<PyInstaller.utils.hooks.collect_submodules>` in the spec file. Be aware though
that, if the package contains unwanted submodules such as test suites, they and
their dependencies will also be pulled into and bloat your application.


.. _missing_modules:

Module classed as MissingModule in xref file
............................................

If the module's entry is annotated with ``MissingModule`` in the ``xref`` file,
PyInstaller thought that it needed the module but couldn't find it.

* If this is your own code that's not findable then that usually means that your
  project structure is to blame. A well formed project structure is `a pip
  installable one
  <https://packaging.python.org/en/latest/tutorials/packaging-projects/>`_ or,
  for less formal projects, a flat directory of ``.py`` files with no
  C/Java-esque ``src`` or ``lib`` or ``deps`` directories.

  PyInstaller, in particular, takes issue with ``__init__.py`` files being
  placed incorrectly in directories that aren't packages. Consider the following
  common but invalid project layout where ``app.py`` contains ``import foo`` or
  ``import bar``.

  .. code-block:: text

      .
      └── src
          ├── foo.py
          ├── bar.py
          ├── __init__.py
          └── app.py

  For ``import foo`` to work, the ``src`` directory must be in Python's module
  search path (:data:`sys.path`) making ``foo.py`` and ``bar.py`` both
  standalone modules. Despite being in the same directory, ``foo`` and ``bar``
  are **not** part of any Python *package*. The presence of ``src/__init__.py``
  however implies that ``src`` is a package and that ``src/foo.py`` and
  ``src/bar.py`` are the submodules ``src.foo`` and ``src.bar``. PyInstaller
  will insert ``src``'s parent directory into :data:`sys.path` meaning that
  ``import foo`` will raise a :class:`ModuleNotFoundError` since ``foo``'s real
  import name is actually ``src.foo``.

* If it's a third party module then this typically indicates that PyInstaller is
  installed in the wrong Python environment. This is all too common amongst
  PyCharm users due to its unfortunate default of creating a new virtual
  environment when you select a project's Python interpreter. Near the beginning
  of PyInstaller's build logs, there's a line saying ``INFO: Python environment:
  /some/path``. That path **must** match the value of :data:`sys.prefix` from
  your IDE (or whatever you normally use to run Python). The surest (albeit
  clunky) way to guarantee this is to print :data:`sys.executable` to get a full
  path to your Python interpreter then, in a terminal use::

      "the/full/path/to/python.exe" -m pip install pyinstaller
      "the/full/path/to/python.exe" -c "import offending_module; print(offending_module.__file__)"  # check it's findable to Python
      "the/full/path/to/python.exe" -m PyInstaller your-code.py  # case sensitive

  If you want the less clunky option, familiarise yourself with :mod:`venv`,
  find and invoke your environment's :ref:`activation script
  <venv-explanation>`, ``pip install pyinstaller`` into this environment then
  build your application as usual. Some IDEs have a built in terminal with the
  option to pre-activate the environment; with this option enabled, running
  ``pip install pyinstaller`` then ``pyinstaller xyz.py`` from such a terminal
  should also work.

* If your are using a pure ``pyproject.toml`` package installed in editable
  mode then be aware that PyInstaller is currently unable to navigate *meta
  path finders* (:issue:`7524`).


Module classed as InvalidSourceModule in xref file
..................................................

If the module's entry is annotated with ``InvalidSourceModule`` then the module
has a syntax error which prevented PyInstaller from running Python's bytecode
compiler on it. This includes using the wrong encoding or `byte order marker
<https://en.wikipedia.org/wiki/Byte_order_mark>`_ for ``.py`` files which is
common if you edit using a Windows-native text editor such as Windows Notepad.
You *should* be able to reproduce this issue under regular (no PyInstaller)
Python.


.. _fixing_file_not_found_error:

Fix a FileNotFoundError
-----------------------

PyInstaller does not collect data files unless it's told to do so. Fixing a
:class:`FileNotFoundError` requires that the application looks for the files in a
relocatable way (i.e. not with a relative path) and that PyInstaller is told to
collect the files into the right place inside your application. If the missing
data file is one of yours then see :ref:`using-file`. If it comes from a package
then the easiest fix is to add :option:`--collect-data=package_name` to your
``pyinstaller`` command.

.. note::

    If you ever think that you need to use different code to lookup data file
    paths in frozen versus unfrozen code paths, then you are putting the data
    files in the wrong place. Data files should be placed where they are
    organically searched for by normal Python code.

.. warning::

    There is a lot of misinformation floating around the internet on this
    subject (mostly due to ChatGPT preaching it as fact). If you ever see
    someone suggest using ``os.chdir()``, ``os.dirname(sys.executable)`` or
    ``sys._MEIPASS``, to locate data files then please help us to purge this
    misinformation by flagging it as wrong.


Fix DLL/shared library load/symbol errors
-----------------------------------------

Issues in loading ``.dll``/``.so``/``.dylib`` files can take three forms:

1. The offending library wasn't packaged at all
2. You have multiple copies of the library installed and the wrong one was picked up
3. You packaged the right library but then ran it on a system with incompatible system library versions

Due to its habit of separating DLLs from the packages they belong to and then
using tenuous methods to let packages find their DLLs, using Anaconda is the
common cause for cases one and two. Switching to a vanilla distribution of
Python is likely to fix such issues. (Note that running a Conda Python but using
only pip install packages is not sufficient to avoid Anaconda-inflicted issues
due to bugs in Conda's Python distributions.)


Fix Distribution/Package metadata not found
-------------------------------------------

If you see either of these errors:

.. code-block:: pytb

    pkg_resources.DistributionNotFound: The 'foo' distribution was not found and is required by the application

.. code-block:: pytb

    importlib.metadata.PackageNotFoundError: No package metadata was found for foo

then add :option:`--copy-metadata=foo` to you ``pyinstaller`` command or
:func:`copy_metadata("foo") <PyInstaller.utils.hooks.copy_metadata>` to the
``datas`` parameter in your spec file.

What the error message is trying to say is that your code or, one of its
dependencies, requires a distribution's *metadata* (the ``*.dist-info``
directories that you find in ``site-packages``). PyInstaller has some automatic
detection for dependencies on metadata but, since it's purely static, only
trivial cases are detected.

.. code-block:: python

    # PyInstaller can detect this:
    importlib.metadata.version("foo")
    # but not this:
    name = "foo"
    importlib.metadata.version(name)


Fix could not get source code error
-----------------------------------

Python only requires bytecode (the contents of ``__pycache__/*.pyc`` files) to
run so PyInstaller does not include raw ``.py`` files as they're effectively a
waste of space. Every now and then however a package (most notably ``PyTorch``)
tries to access original Python sources which leads to an exception like:

.. code-block:: pytb

    Traceback (most recent call last):
    ...
      File "foo/bar/__init__.py", line 31, in <module>
      File "inspect.py", line 1147, in getsource
      File "inspect.py", line 1129, in getsourcelines
      File "inspect.py", line 958, in findsource
    OSError: could not get source code

Unfortunately, the error message rarely indicates which object's source code it
was looking for so you may have to do some digging to find it. You can either:

* Take the filename and line number from the line above ``getsource`` in the
  error's stacktrace, navigate to that filename and line number in
  ``site-packages`` and read around to trace which module or function is being
  given to :func:`inspect.getsource`.

* :ref:`Enable pdb debugging <interactive debugging>`, wait for your application
  to fail and drop into the debugger, then query ``object.__name__`` for modules
  or ``object.__module__`` for functions.

The module you find, or the module in which the function is defined, needs to
have its raw ``.py`` file collected into your application. Source collection is
controlled by the ``.spec`` file only :ref:`module_collection_mode <module
collection mode>` option.

Using the most frequent offender as an example, if a module called ``foo.bar``
contains ``@torch.jit.script`` (which ultimately calls :func:`inspect.getsource`
on the function it's decorating) then edit the ``a = Analysis(...)`` part your
spec file accordingly::

    a = Analysis(
        ...
        module_collection_mode={
            "foo.bar": "py+pyz",
        },
    )


Fix backend/language/translation/implementation/model/something obscure not found/supported
-------------------------------------------------------------------------------------------

It's not uncommon for packages to raise custom (sometimes misinformative)
exceptions when accessing something that PyInstaller didn't know to collect.

Consider the following simplified functions, noting the common theme of choosing
or iterating over some resource that PyInstaller struggles to detect, usually
influenced by some variable, then raising an exception which at best, does
nothing to indicate the original packaging issue and at worst, tells you
something untrue. ::

    def load_translations_file(language):
        # Without explicitly collecting the translations/*.po files, the
        # following will claim that translations for any language don't exist.
        path = pathlib.Path(__file__).with_name(f"translations/{language}.po")
        if not path.is_file():
            raise UnsupportedLanguageError(f"No translation exists for {language}")
        return path.read_text("utf-8")

    def native_implementation():
        # PyInstaller can't detect imports made via importlib so, by default,
        # the code below will on any OS land on raising the NotImplementedError.
        try:
            return importlib.import_module(f"some_package._{sys.platform}")
        except ImportError:
            raise NotImplementedError(f"{sys.platform} OS is not supported") from None

    def find_backend():
        # Without explicitly collecting package metadata, the following for loop
        # will iterate zero times.
        for entry_point in importlib.metadata.entry_points(group="xxx_backends"):
            return entry_point.load()
        raise NoBackendFound("An xxx implementation is required")

Since these exceptions and their origins are specific to each case, you'll have
to do your own digging to diagnose them. Take the filenames and line numbers
from the error's stacktrace, lookup the corresponding source code from your
original packages in ``site-packages`` and try to ascertain what it was really
looking for before raising the exception (usually either modules, data files or
entry points). For reference, the above examples would respectively be fixed by:

1. :option:`--collect-data=offending.package`

2. :option:`--collect-submodules=some_package` or
   :option:`--hiddenimport=some_package._current_platform`

3. :func:`collect_entry_point("xxx_backends")
   <PyInstaller.utils.hooks.collect_entry_point>` (spec file only)


Application fails only in windowed/noconsole mode
-------------------------------------------------

Python's default exception handling behaviour (writing error messages to the
console) doesn't make any sense without a console so the first step to
addressing any windowed mode only issue is to redirect all exceptions to
somewhere you can get at them.


.. _stacktrace_without_a_console:

Stacktraces without a console
.............................

The quick and dirty way to capture stacktraces is to wrap your code in a big
try/except then dump the stacktrace into a log file::

    try:
        # Your code here **including all imports**
    except:
        import traceback
        with open("C:/Users/you/crash.txt", "w", encoding="utf-8") as f:
            f.write("".join(traceback.format_exception(value))
        raise

Note that the log path **must not** be:

* relative (since the application's working directory is unlikely to be
  writable)

* inside the application or anchored to the application's location (in case the
  application is installed into a read-only location)

If you wish to generalise the log path to make the above portable then use
:func:`platformdirs.user_log_dir` to locate a directory which you can
write to without running afoul of permission errors or macOS's sandboxing.

If your application is multi-threaded or uses callbacks, consider instead
setting :func:`sys.excepthook` so that exceptions on background threads are also
handled.

.. collapse:: Qt example of exception handling with an exception hook

    .. code-block:: python

        import sys
        import pathlib
        import traceback
        import datetime
        import platformdirs


        def excepthook(exctype, value, traceback):
            # Preserve original stderr exception reporting if possible.
            if sys.stderr:
                sys.stderr.write("".join(traceback.format_exception(value)))

            # Write to log file.
            logs_root = pathlib.Path(platformdirs.user_log_dir("my-application"))
            logs_root.mkdir(exist_ok=True, parents=True)
            log_path = logs_root / f"crash-{datetime.datetime.now()}.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("".join(traceback.format_exception(value)))

            # Create pop-up error dialog. Do it last since it's the most likely to fail.
            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
            box = QtWidgets.QMessageBox()
            box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            box.setText("Unexpected Error: " + repr(value))
            box.setInformativeText(
                "XYZ Application has encountered an error. Should you wish to report this, please "
                "copy the details below into an issue at "
                '<a href="https://example.com/issues">https://example.com/issues</a>'
            )
            box.setStyleSheet("QDialogButtonBox{min-width: 700px;}")
            box.setTextFormat(QtCore.Qt.TextFormat.RichText)
            box.setDetailedText("".join(traceback.format_exception(value)))
            box.exec()


        sys.excepthook = excepthook

        # Defer as many imports as possible until after installing the excepthook
        from PyQt6 import QtWidgets, QtCore

        # main application here


Attribute errors using sys.stdout or sys.stderr on Windows
..........................................................

The common windowed-only issue is expecting the standard stream to exist. If you
get an error which looks like::

    AttributeError: 'NoneType' object has no attribute 'flush'

(where ``flush`` may be replaced with ``write``, ``read``, ``fileno`` or
``isatty``) then read :ref:`this <no_console_stdout_stderr>`.


Application fails only when launched via double click
-----------------------------------------------------

To debug this case, first set up :ref:`console-less diagnostics
<stacktrace_without_a_console>` so that you have a stacktrace to work with.

With the exception of on macOS (see below), launching from a terminal and via
double click are equivalent enough that discrepancies in behavior invariably
turn out to be indirect causes such as:

* Non-relocatable resource location. If you get a :class:`FileNotFoundError`
  then see :ref:`using-file`.

* Using Anaconda then verifying your application from a conda shell. Using a
  terminal with a conda environment activated masks missing dependency issues
  because your application can still load them from the original conda
  environment. *Deactivating* the conda environment does not prevent this
  because it doesn't truly deactivate anything (library search paths remain set)
  so it will still hide bugs. If you are using Anaconda then verify your
  application from a new vanilla (non conda) terminal to see if it gets the same
  error.


macOS limited environment
.........................

On macOS, there is no such thing as a customized global environment variable.
Environment variables can be configured in shell initialization files
(``~/.bashrc``, ``~/.zshrc``, ``~/.profile``, ``/etc/profile`` and
``/etc/paths.d/*``) but these all are ignored by desktop applications (or any
process that isn't ran from the Terminal app). Some environment variables that
you may be taking for granted will therefore not exist. Below is an example of
the :data:`os.environ` that a macOS desktop application receives:

.. code:: json

    {
      "USER": "brenainn",
      "COMMAND_MODE": "unix2003",
      "__CFBundleIdentifier": "test_app",
      "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
      "LOGNAME": "brenainn",
      "SSH_AUTH_SOCK": "/private/tmp/com.apple.launchd.n5iHuxeC4n/Listeners",
      "HOME": "/Users/brenainn",
      "SHELL": "/bin/zsh",
      "TMPDIR": "/var/folders/m0/r_04r9v530v132v7n1v00000p/T/",
      "__CF_USER_TEXT_ENCODING": "0x1F6:0:2",
      "XPC_SERVICE_NAME": "application.test.134245318.134245425",
      "XPC_FLAGS": "0x0"
    }

The key things to note:

* ``PATH`` does not contain ``/opt/homebrew/bin`` or ``/usr/local/bin``.
  **Custom or homebrew-installed command line applications will not be
  findable**. This, combined with all the default locations in ``PATH`` being
  read only (even to root users), makes it impossible to depend on anything that
  is not a builtin part of macOS unless you bundle it and its dependencies into
  your own application (use :option:`--add-binary` then add the directory you
  put it in to ``os.environ["PATH"]`` at runtime).

* ``LANG`` and the ``LC_*`` variables are unset. The current locale will be
  undefined. :func:`locale.getlocale` and :func:`locale.getdefaultlocale` will
  both return ``(None, None)``. Your application must be tolerant to this.

For convenience, you can approximate running your original or frozen code in
this limited environment from a terminal by using ``env -i`` (clear all
environment variables)::

    env -i /absolute/path/to/bin/python3 your-application.py
    env -i ./dist/your-application.app/Contents/MacOS/your-application


macOS crash with Report to Apple prompt
.......................................

TBC: Missing entitlements + codesign issues


GUI icon is not shown
---------------------

GUI frameworks typically do not raise the *missing file* error that you'd expect
to get when they're told to load an icon from a non-existent file. If your icon
is being ignored then put the following **before** where you load it then
troubleshoot it :ref:`as you would<fixing_file_not_found_error>` any other
missing file error. ::

    if not os.path.exists(icon_path):
        raise FileNotFoundError(icon_path)

This pattern is also sometimes seen with CSS, QML or template files.


Handling relative imports in entry point script
-----------------------------------------------

PyInstaller doesn't support relative imports in the entry point script since it
has no way of determining which package (or subpackage) the script belongs to.
Attempting such an import will give an error like:

.. code-block:: pytb

    Traceback (most recent call last):
      File "__main__.py", line 1, in <module>
    ImportError: attempted relative import with no known parent package

The ideal fix is to replace the relative imports with absolute ones (i.e.
replace ``from . import xyz`` with ``from my_package import xyz``). If modifying
the code is not an option then the alternative is to create a wrapper entry
point which imports and runs the package's top level code then run PyInstaller
on that script. ::

    # Wrapper script for freezing python -m some_package
    # Run pyinstaller on me
    from some_package.__main__ import some_function_usually_called_main
    some_function_usually_called_main()


Builtins ``exit()`` and ``help()`` are undefined
------------------------------------------------

The builtin ``help()``, ``exit()``, ``quit()`` and ``copyright``
functions/variable are not truly part of the Python language. The :mod:`site`
module injects them into :mod:`builtins` exclusively for use in interactive
Python consoles. PyInstaller applications run with the interpreter configured to
something akin to Python's :option:`-S` mode (disable :mod:`site`) meaning that
trying to reference any of these *not really builtins* will result in a
:class:`NameError`:

.. code-block:: pytb

    NameError: name 'exit' is not defined

You are not expected to be using these functions in code. Replace ``exit()``
with :func:`sys.exit` for a successful early program exit or :class:`raise
SystemExit("error message here") <SystemExit>` for user errors. If, during a
debugging session, you want to call :func:`help` then run ``import site;
site.sethelper()`` first and it will be defined.


Application runs on one machine but not another
-----------------------------------------------

On UNIX (macOS especially, Linux \*BSD, …) applications rely on symlinks which
most archiving techniques, such as zip files, inadvertently flatten. Flattened
symlinks can cause crashes which are reproducible just by unpacking the
application onto your own machine. See :ref:`distributing_symlinks`.

If you're getting DLL/shared library or symbol errors and the OS that you're
running on is older than the one you built on (on Linux, the *age* of a given
platform is most meaningfully quantified by the version reported by ``ldd
--version`` rather than the kernel or distribution version) then all bugs are
features since at best, there's nothing to ensure that the files that you gave
PyInstaller to put in your application are compatible with the target platform.
At worst, you will have binaries which are compiled specifically for >= your OS
version. See :ref:`supporting older platforms`.

If none of the above, your application is probably broken everywhere but
something on your first machine is hiding the issue. There's not much to said
here beyond look at the stacktrace and treat it as if it happened on your own
machine.


*Different behaviors* when frozen
---------------------------------

PyInstaller's sphere of interference is almost exclusively limited to packaging
issues. When code has behaved differently in a way that doesn't appear to have
any link to packaging such as calculations returning different values or
detection software giving wrong levels of accuracy, it invariably turns out to
be due to ``pyinstaller`` being ran from the wrong Python environment, giving it
different versions of dependencies. See the advice under :ref:`MissingModule in
xref file <missing_modules>` regarding :data:`sys.prefix` and
:data:`sys.executable` for how to not end up in this situation.


.. _interactive debugging:

Interactive debugging
~~~~~~~~~~~~~~~~~~~~~

IDE debuggers can not interact with frozen applications and you may find
yourself falling back to tedious *insert print statements everywhere* debugging.
However, there are command line debuggers that can be injected almost anywhere,
including into a PyInstaller application. From the standard library, use
:func:`code.interact` to pause and interact with your application::

    # Enter REPL session. Place just before a troublesome line of code
    import code
    code.interact(local={**globals(), **locals()})

    # Alternative – like the above but with readline completion (requires a
    # working readline installation)
    import code
    import readline
    import rlcompleter
    vars = {**globals(), **locals()}
    readline.set_completer(rlcompleter.Completer(vars).complete)
    readline.parse_and_bind("tab: complete")
    code.InteractiveConsole(vars).interact()

Or use :mod:`pdb` to enter a debugging session whenever an exception occurs::

    # Enter a pdb (debugger) session on any error
    try:
        # Your main code here
    except:
        import pdb, traceback
        traceback.print_exc()
        pdb.post_mortem()

Both methods have 3rd party equivalents, ptpython_ and pdbp_ respectively,
giving you the above but with color and fancy completion. Use::

    import ptpython
    ptpython.embed(globals=globals(), locals=locals())

in place of the :func:`code.interact` example or replace ``pdb`` with ``pdbp``
in the :func:`~pdb.post_mortem` example.

.. note::

    IPython also has an embeddable REPL but, due to it's large and highly
    ambiguous dependency tree, IPython and PyInstaller are best kept as far away
    from each other as possible.

.. _ptpython: https://github.com/prompt-toolkit/ptpython
.. _pdbp: https://github.com/mdmintz/pdbp
