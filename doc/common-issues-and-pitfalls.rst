.. _common issues:

==========================
Common Issues and Pitfalls
==========================

This section attempts to document common issues and pitfalls that
users need to be aware of when trying to freeze their applications with
PyInstaller, as certain features require special care and considerations
that might not be obvious when developing and running unfrozen python
programs.


Requirements Imposed by Symbolic Links in Frozen Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with PyInstaller 6.0, the frozen application bundles generated
by PyInstaller on non-Windows systems make extensive use of symbolic
links. Therefore, creation and distribution of PyInstaller-frozen
applications requires special considerations.

Failing to preserve symbolic links will turn them into full file copies;
the duplicated files will balloon the size of your frozen application,
and may also lead to run-time issues.

.. Note::
    In PyInstaller versions prior to 6.0, symbolic links were used only
    in generated :ref:`macOS .app bundles <macOS app bundles>`.
    From 6.0 on, they are also used in "regular" POSIX builds on all
    POSIX systems (macOS, Linux, FreeBSD, etc.), both in ``onefile`` and
    ``onedir`` mode.

In ``onefile`` builds, the use of symbolic links imposes run-time
requirements for the temporary directory into which the program unpacks
itself before running - **the temporary directory must be located on
filesystem that supports symbolic links**. Otherwise, the program will
fail to unpack itself, as it will encounter an error when trying to
(re)create a symbolic link.

The ``onedir`` builds can only be generated on a filesystem that supports
symbolic links. Similarly, they can only be moved or copied to a
filesystem that supports symbolic links. If you plan to distribute your
``onedir`` application as an archive, ensure that archive format supports
preservation of symbolic links.

.. Note::
    When copying the generated ``onedir`` application bundle, ensure
    that you use copy command with options that preserve symbolic links.
    For example, on Linux, both ``cp -fr <source> <dest>`` and ``cp -fR <source> <dest>``
    preserve symbolic links. On macOS, on the other hand, ``cp -fr <source> <dest>``
    **does not** preserve symbolic links, while ``cp -fR <source> <dest>`` does.

.. Note::
    Creation of a ``zip`` archive by default **does not** preserve symbolic
    links; preservation needs to be explicitly enabled via
    ``--symlinks`` / ``-y`` command-line switch to the ``zip`` command.


.. _launching external programs:

Launching External Programs from the Frozen Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In a PyInstaller-frozen application, the run-time environment of the
application's process is often modified to ensure that when it comes
to loading of the shared libraries, the bundled copies of shared
libraries are preferred over the copies that might be available on
the target system. The exact way of modifying the library search order
(environment variables versus low-level API) depends on the operating
system, but in general, changes made to the frozen application's run-time
environment are also inherited by subprocesses launched by the frozen
application. This ensures that the application itself (for example,
the binary python extensions it loads) as well as bundled helper programs
that the application might run as a subprocess (for example, ``gspawn``
when using ``GLib``/``Gio`` via ``gi.repository`` on Windows,
``QtWebEngineHelper`` from ``PyQt`` and ``PySide`` packages, and so on)
use the shared libraries they they were originally built against and thus
have compatible ABI. This makes frozen applications portable, more or
less self-contained, and isolated from the target environment.

The above paradigm is inherently at odds with code that is trying
to launch an **external program**, i.e., a program that is available on
the target system (and launched, for example, via :func:`subprocess.run`).
System-installed external programs are built against shared
libraries provided by the system, which might be of different and
incompatible versions compared to the ones bundled with the frozen
application. And because in the run-time environment of the
PyInstaller-frozen application (which is inherited by the launched
subprocesses) the library search path is modified to prefer the
bundled shared libraries, trying to launch an external program might
fail due to shared library conflicts.

Therefore, if your code (or the 3rd party code you are using) is trying
to launch an external program, you need to ensure that the changes
to the library search paths, made for the frozen application's main
process, are reset or reverted. The specifics of such **run-time environment
sanitization** are OS-dependent, and are outlined in the following
sub-sections.

.. Note::
    On some operating systems, the library search path is modified only
    via environment variables; in such cases, if you are launching
    the subprocess in your code (e.g., via :func:`subprocess.run`),
    you can pass the sanitized environment to the subprocess via the
    ``env`` argument. This way, only the environment of the sub-process
    is modified, while the environment of the frozen application
    itself (i.e., its search paths) are left unchanged.

    If this is not possible, however, you might need to temporarily
    sanitize the environment of the main application, launch the external
    program (so it inherits the sanitized environment), and then restore
    the main application's environment back to the original
    (PyInstaller-adjusted) version.

    If you are launching the external program *after* all modules
    have been imported and their dependencies have been loaded, and if
    your frozen application does not include any helper programs that might
    be launched after your external program, you can simply sanitize
    main application's run-time environment, without having to
    worry about restoring it after your external program is launched.

Linux and Unix-like OSes
------------------------------

On POSIX systems (with exception of macOS and Cygwin - see their dedicated sub-sections),
the library search path is modified via the ``LD_LIBRARY_PATH`` environment
variable (``LIBPATH`` on AIX).

During the frozen application's startup, the PyInstaller's bootloader
checks whether the ``LD_LIBRARY_PATH`` environment variable is already
set, and, if necessary, creates a copy of its contents into
``LD_LIBRARY_PATH_ORIG`` environment variable. Then, it modifies
``LD_LIBRARY_PATH`` by prepending the application's top level directory
(i.e., the path that is also available in ``sys._MEIPASS``).

Therefore, prior to launching an external program, the ``LD_LIBRARY_PATH``
should be either cleared (to use the system default) or reset to the value
stored in ``LD_LIBRARY_PATH_ORIG`` (if available). See :ref:`library path considerations`
for details and an example.

Windows
-------

On Windows, the PyInstaller's bootloader sets the library search path
to the top-level application directory (i.e., the path that is also
available in ``sys._MEIPASS``) using the
`SetDllDirectoryW <https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setdlldirectoryw>`__
Win32 API function.

As noted in the API documentation, calling this function also affects
the children processes started from the frozen application. To undo
the effect of this call and restore standard search paths,
``SetDllDirectory`` function should be called with ``NULL`` argument.
As discussed in :issue:`3795`, the most practical way to achieve this from
python code is to use ``ctypes``, for example::

    import sys
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)

PyInstaller's bootloader does not modify the ``PATH`` environment variable.
However, the ``PATH`` environment variable may be modified by run-time
hooks for specific packages, in order to facilitate discovery of dynamic
dependencies that are loaded at run-time.

Therefore, it may also be necessary to sanitize the ``PATH`` environment
variable, and (temporarily) remove any paths anchored in top-level application
directory (``sys._MEIPASS``) prior to launching the external program.

macOS
-----

On macOS, PyInstaller rewrites the library paths in collected binaries
to refer to copies (or symbolic links) in the top-level application
directory, relative to the binary's location. Therefore, PyInstaller's
bootloader does not need to modify the ``DYLD_LIBRARY_PATH`` environment
variable.

However, the ``DYLD_LIBRARY_PATH`` environment variable may be modified
by run-time hooks for specific packages, in order to facilitate discovery
of dynamic dependencies that are loaded at run-time.

Therefore, it may also be necessary to sanitize the ``DYLD_LIBRARY_PATH``
environment variable, and (temporarily) remove any paths anchored in
top-level application directory (``sys._MEIPASS``) prior to launching
the external program.

.. Note::
    If you are building a `macOS .app bundle <macOS app bundles>`_, you
    should be aware that when launched from Finder, the app process runs
    in an environment with reduced set of environment variables.
    Most notably, the ``PATH`` environment variable is set to only
    ``/usr/bin:/bin:/usr/sbin:/sbin``. Therefore, programs installed in
    locations that are typically in ``PATH`` when running a Terminal
    session (e.g., ``/usr/local/bin``, ``/opt/homebrew/bin``) will not
    be visible to the app, unless referenced by their full path.

Cygwin
------

Under Cygwin, the ``LD_LIBRARY_PATH`` environment variable is used by
``dlopen()`` when trying to resolve a library that was given only by a
basename (without path), while the linked dependencies of binaries and
loaded DLLs are resolved by Windows loader, whose search path is controlled
by the `SetDllDirectoryW <https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setdlldirectoryw>`_
Win32 API function.

The PyInstaller's bootloader sets the library search path to the top-level
application directory (i.e., the path that is also available in ``sys._MEIPASS``)
using *both mechanisms*; therefore, both Linux-specific and Windows-specific
considerations from earlier sub-sections apply.


.. _multiprocessing:

Multi-processing
~~~~~~~~~~~~~~~~

Currently, the only supported multi-processing framework is the
:mod:`multiprocessing` module from the Python standard library,
and even that requires you to make a :func:`multiprocessing.freeze_support`
call before using any :mod:`multiprocessing` functionality.

A typical symptom of failing to call :func:`multiprocessing.freeze_support`
before your code (or 3rd party code you are using) attempts to make use of
:mod:`multiprocessing` functionality is an endless spawn loop of your
application process.

.. Note::
    :mod:`multiprocessing` supports different start modes: ``spawn``,
    ``fork``, and ``forkserver``. Of these, ``fork`` is the only one
    that might work in the frozen application without calling
    ``multiprocessing.freeze_support()``.
    The default start method on Windows and macOS is ``spawn``, while
    ``fork`` is default on other POSIX systems (however, Python 3.14
    plans to change that).

Why is calling `multiprocessing.freeze_support()` required?
-----------------------------------------------------------

As implied by its name, the :mod:`multiprocessing` module spawns several
processes; typically, these are worker processes running your tasks. On
POSIX systems, ``spawn`` and ``forkserver`` start methods also spawn
a dedicated resource tracker process that tracks and handles clean-up
of unlinked shared resources (e.g., shared memory segments, semaphores).

The sub-processes started by :mod:`multiprocessing` are spawned using
:data:`sys.executable` - when running an unfrozen python script, this
corresponds to your python interpreter executable (e.g., ``python.exe``).
The command-line arguments instruct the interpreter to run a corresponding
function from the :mod:`multiprocessing` module. For example, the spawned
worker process on Windows looks as follows::

    python.exe -c "from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=6872, pipe_handle=520)" --multiprocessing-fork

Similarly, when using the ``spawn`` start method on a POSIX system, the
resource tracker process is started with the following arguments::

    python -c from multiprocessing.resource_tracker import main;main(5)

while the worker process is started with the following arguments::

    python -c "from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=6, pipe_handle=8)" --multiprocessing-fork

In the frozen application, ``sys.executable`` points to your application
executable. So when the :mod:`multiprocessing` module in your main process
attempts to spawn a subprocess (a worker or the resource tracker), it runs
another instance of your program, with the following arguments for resource
tracker::

    my_program -B -S -I -c "from multiprocessing.resource_tracker import main;main(5)"

and for the worker process::

    my_program --multiprocessing-fork tracker_fd=6 pipe_handle=8

On Windows, the worker process looks similar::

    my_program.exe --multiprocessing-fork parent_pid=8752 pipe_handle=1552

If no special handling is in place in the program code, the above
invocations end up executing your program code, which leads to one of
the two outcomes:

* this second program instance again reaches the point where
  :mod:`multiprocessing` module attempts to spawn a subprocess, leading to
  an endless recursive spawn loop that eventually crashes your system.

* if you have command-line parsing implemented in your program code,
  the command-line parser raises an error about unrecognized parameters.
  Which may lead to periodic attempts at spawning the resource tracker
  process.

Enter :func:`multiprocessing.freeze_support` - PyInstaller provides a
custom override of this function, which **is required to be called on all
platforms** (in contrast to original standard library implementation,
which, as suggested by its documentation, caters only to Windows). Our
implementation inspects the arguments (:data:`sys.argv`) passed to the process,
and if they match the arguments used by :mod:`multiprocessing` for a worker
process or resource tracker, it diverts the program flow accordingly
(i.e., executes the corresponding :mod:`multiprocessing` code and exits
after finished execution).

This ensures that :mod:`multiprocessing` sub-processes, while re-using
the application executable, execute their intended :mod:`multiprocessing`
functionality instead of executing your main program code.

When to call `multiprocessing.freeze_support()`?
------------------------------------------------

The rule of thumb is, :func:`multiprocessing.freeze_support` should be
called before trying to use any of :mod:`multiprocessing` functionality
(such as spawning a process or opening process pool, or allocating a
shared resource, for example a semaphore).

Therefore, as documented in original implementation of
:func:`multiprocessing.freeze_support`, a typical call looks like this::

    from multiprocessing import Process, freeze_support

    def f():
        print('hello world!')

    if __name__ == '__main__':
        freeze_support()
        Process(target=f).start()


However, there are scenarios where you might need to make the call even
sooner, before (at least some of) the imports at the top of your script.
This might be necessary if your script imports a module that does one of
the following during its initialization (i.e., when it is imported):

* makes use of :mod:`multiprocessing` functionality.

* parses command-line arguments for your program.

* imports and initializes a GUI framework. While this might not result
  in an error, it should be avoided in the worker processes by diverting
  the program flow before it happens.

Similarly, if both of the following conditions are true:

* your script imports several heavy-weight modules that are needed by
  the main program but not by the worker process

* your script does not directly use :mod:`multiprocessing` functionality
  itself, but rather imports a 3rd party module and calls a function from
  it that uses :mod:`multiprocessing`,

then it might be worth placing the :func:`multiprocessing.freeze_support`
before the imports, to avoid unnecessarily slowing the worker processes::

    # Divert the program flow in worker sub-process as soon as possible,
    # before importing heavy-weight modules.
    if __name__ == '__main__':
        import multiprocessing
        multiprocessing.freeze_support()

    # Import several heavy-weight modules
    import numpy as np
    import cv2
    # ...
    import some_module

    if __name__ == '__main__':
        # Call some 3rd party function that internally uses multiprocessing
        some_module.some_function_that_uses_multiprocessing()

.. Note::
    If :mod:`multiprocessing` is used only in an external module that
    is imported and used by your script, then the :mod:`multiprocessing`
    worker sub-process needs to load and initialize only that module;
    therefore, diverting the program flow using
    :func:`multiprocessing.freeze_support` before performing heavy-weight
    imports avoids unnecessarily slowing down the worker process.

    On the other hand, if your main script (also) uses :mod:`multiprocessing`
    functionality, then the corresponding worker sub-process also need
    to execute the remainder of your script, including the imports; which
    limits the performance benefits of an early
    :func:`multiprocessing.freeze_support` call.

What about other multi-processing frameworks?
---------------------------------------------

The Python ecosystem provides several alternatives to the :mod:`multiprocessing`
from the Python standard library - **none of them are supported
by PyInstaller**.

The PyInstaller-frozen application does not have access to python
interpreter executable (``python`` or ``python.exe``) and its environment,
and must therefore use its embedded python interpreter. Therefore, any
other alternative python-based multi-processing solution would also
need to spawn its worker subprocesses using the program executable
(:data:`sys.executable`).

Even if the alternative multi-processing framework uses :data:`sys.executable`
to spawn its subprocesses, your program code would need to be made aware
of such attempts, and handle them accordingly. In other words, you would
need to implement inspection of program arguments (:data:`sys.argv`), detect
attempts at spawning worker subprocesses based on the arguments, and
divert the program flow into corresponding framework's function instead
of letting it reach your main program code.


.. _independent subprocess:

Using ``sys.executable`` to spawn subprocesses that outlive the application process / Implementing application restart
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some scenarios, you might want your frozen application to spawn
an independent instance of itself. This includes the pattern of
application "restarting itself" by spawning a subprocess via
:data:`sys.executable` and exiting the current process.

In such scenario, the spawned process is expected to outlive the current
application process, in spite of being its subprocess. This is different
from various multi-processing scenarios, where worker subprocesses spawned
using :data:`sys.executable` usually do not outlive the main application
process.

This distinction is important especially in the context of ``onefile``
builds, where the application process is spawned from a parent process
that performs the cleanup of the application's temporary files when the
application process exits. When subprocesses are spawned from application
process via :data:`sys.executable` and are not expected to outlive the
application process (e.g., multiprocessing scenario), they can safely
re-use the already-unpacked temporary files.

In contrast, if the spawned subprocess is expected to outlive the application
process that spawned it (e.g., a "restart scenario"), the temporary files
cannot be re-used, as they would be removed once the current process exits;
the spawned subprocess would end up missing files and, on Windows, it might
also interfere with the cleanup itself due to attempts at accessing the files.

Therefore, if you need to spawn a subprocess using :data:`sys.executable`
that will outlive the current application process, you need to ensure
that is spawned as an independent instance. This is done by setting
the :envvar:`PYINSTALLER_RESET_ENVIRONMENT` environment variable to ``1``
when spawning the process, for example::

    # Restart the application
    subprocess.Popen([sys.executable], env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"})
    sys.exit(0)

.. versionchanged:: 6.9
    The above requirement was introduced in PyInstaller 6.9, which changed
    the way the bootloader treats a process spawned via the same executable
    as its parent process. Whereas previously the default assumption was that
    it is running a new instance of (the same) program, the new assumption
    is that the spawned process is some sort of a worker subprocess that can
    reuse the already-unpacked resources. This change was done because the
    worker-process scenarios are more common, and more difficult to explicitly
    accommodate across various multiprocessing frameworks and other code
    that spawns worker processes via ``sys.executable``.


``sys.stdin``, ``sys.stdout``, and ``sys.stderr`` in ``noconsole``/``windowed`` Applications (Windows only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Windows, the :option:`--noconsole` allows you to build a frozen
application using the "windowed" bootloader variant, which was built
with ``/SUBSYSTEM:WINDOWED`` option (as opposed to ``/SUBSYSTEM:CONSOLE``;
see `here <https://learn.microsoft.com/en-us/cpp/build/reference/subsystem-specify-subsystem>`__
for details), and thus has no console attached. This is similar to the
*windowed python interpreter executable*, ``pythonw.exe``, which can be
used to run python scripts that do not require a console, nor want to
open a console window when launched.

A direct consequence of building your frozen application in the
windowed/no-console mode is that standard input/output file objects,
:data:`sys.stdin`, :data:`sys.stdout`, and :data:`sys.stderr` are unavailable,
and are set to ``None``. The same would happen if you ran your unfrozen
code using the ``pythonw.exe`` interpreter, as documented under
:data:`sys.__stderr__` in Python standard library documentation.

Therefore, if your code (or the 3rd party code you are using) naively
attempts to access attributes of :data:`sys.stdout` and :data:`sys.stderr`
objects without first ensuring that the objects are available, the frozen
application will raise an ``AttributeError``; for example, trying to
access ``sys.stderr.flush`` will result in ``'NoneType' object has no
attribute 'flush'``.

The best practice would be to fix the offending code so that it checks
for availability of the standard I/O file objects before trying to use
them; this will ensure compatibility with both ``pythonw.exe``
interpreter and with PyInstaller's ``noconsole`` mode. However, if fixing
the problem is not an option (for example, the problem originates from
a 3rd party module and is beyond your control), you can work around it
by setting dummy file handles at the very start of your program::

    import sys
    import os

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    # the rest of your imports

    # and the rest of your program

.. Note::
    If you plan to build your frozen application in windowed/no-console
    mode, we recommend that you first try running your unfrozen script
    using the ``pythonw.exe`` interpreter to ensure that it works correctly
    when console is unavailable.
