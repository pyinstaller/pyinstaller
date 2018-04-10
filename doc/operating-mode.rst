What |PyInstaller| Does and How It Does It
============================================================

This section covers the basic ideas of |PyInstaller|.
These ideas apply to all platforms.
Options and special cases are covered below, under :ref:`Using PyInstaller`.

|PyInstaller| reads a Python script written by you.
It analyzes your code to discover every other module and library
your script needs in order to execute.
Then it collects copies of all those files -- including
the active Python interpreter! -- and puts them with
your script in a single folder,
or optionally in a single executable file.

For the great majority of programs, this can be done with one short command, ::

    pyinstaller myscript.py

or with a few added options, for example a windowed application
as a single-file executable, ::

    pyinstaller --onefile --windowed myscript.py

You distribute the bundle as a folder or file to other people,
and they can execute
your program.
To your users, the app is self-contained.
They do not need to install any particular version of Python or any modules.
They do not need to have Python installed at all.

.. Note::

    The output of  |PyInstaller| is specific to the active operating system
    and the active version of Python.
    This means that to prepare a distribution for:

        * a different OS
        * a different version of Python
        * a 32-bit or 64-bit OS

    you run |PyInstaller| on that OS, under that version of Python.
    The Python interpreter that executes |PyInstaller| is part of
    the bundle, and it is specific to the OS and the word size.


Analysis: Finding the Files Your Program Needs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What other modules and libraries does your script need in order to run?
(These are sometimes called its "dependencies".)

To find out, |PyInstaller| finds all the ``import`` statements
in your script.
It finds the imported modules and looks in them for ``import``
statements, and so on recursively, until it has a complete list of
modules your script may use.

|PyInstaller| understands the "egg" distribution format often used
for Python packages.
If your script imports a module from an "egg", |PyInstaller| adds
the egg and its dependencies to the set of needed files.

|PyInstaller| also knows about many major Python packages,
including the GUI packages
Qt_ (imported via PyQt_ or PySide_), WxPython_, TkInter_, Django_,
and other major packages.
For a complete list, see `Supported Packages`_.

Some Python scripts import modules in ways that |PyInstaller| cannot detect:
for example, by using the ``__import__()`` function with variable data,
using ``imp.find_module()``,
or manipulating the ``sys.path`` value at run time.
If your script requires files that |PyInstaller| does not know about,
you must help it:

* You can give additional files on the ``pyinstaller`` command line.
* You can give additional import paths on the command line.
* You can edit the :file:`{myscript}.spec` file
  that |PyInstaller| writes the first time you run it for your script.
  In the spec file you can tell |Pyinstaller| about code modules
  that are unique to your script.
* You can write "hook" files that inform |Pyinstaller| of hidden imports.
  If you create a "hook" for a package that other users might also use,
  you can contribute your hook file to |PyInstaller|.

If your program depends on access to certain data files,
you can tell |PyInstaller| to include them in the bundle as well.
You do this by modifying the spec file, an advanced topic that is
covered under :ref:`Using Spec Files`.

In order to locate included files at run time,
your program needs to be able to learn its path at run time
in a way that works regardless of
whether or not it is running from a bundle.
This is covered under :ref:`Run-time Information`.

|PyInstaller| does *not* include libraries that should exist in
any installation of this OS.
For example in Linux, it does not bundle any file
from :file:`/lib` or :file:`/usr/lib`, assuming
these will be found in every system.


.. _Bundling to One Folder:

Bundling to One Folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you apply |PyInstaller| to :file:`myscript.py` the default
result is a single folder named :file:`myscript`.
This folder contains all your script's dependencies,
and an executable file also named :file:`myscript`
(:file:`myscript.exe` in Windows).

You compress the folder
to :file:`myscript.zip` and transmit it to your users.
They install the program simply by unzipping it.
A user runs your app by
opening the folder and launching the :file:`myscript` executable inside it.

It is easy to debug problems that occur when building the app
when you use one-folder mode.
You can see exactly what files |PyInstaller| collected into the folder.

Another advantage of a one-folder bundle
is that when you change your code, as long
as it imports `exactly the same set of dependencies`, you could send out
only the updated :file:`myscript` executable.
That is typically much smaller
than the entire folder.
(If you change the script so that it imports more
or different dependencies, or if the dependencies
are upgraded, you must redistribute the whole bundle.)

A small disadvantage of the one-folder format is that the one folder contains
a large number of files.
Your user must find the :file:`myscript` executable
in a long list of names or among a big array of icons.
Also your user can create
a problem by accidentally dragging files out of the folder.

.. _how the one-folder program works:

How the One-Folder Program Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A bundled program always starts execution in the |PyInstaller| |bootloader|.
This is the heart of the ``myscript`` executable in the folder.

The |PyInstaller| |bootloader| is a binary
executable program for the active platform
(Windows, Linux, Mac OS X, etc.).
When the user launches your program, it is the |bootloader| that runs.
The |bootloader| creates a temporary Python environment
such that the Python interpreter will find all imported modules and
libraries in the ``myscript`` folder.

The |bootloader| starts a copy of the Python interpreter
to execute your script.
Everything follows normally from there, provided
that all the necessary support files were included.

(This is an overview.
For more detail, see :ref:`The Bootstrap Process in Detail` below.)


.. _Bundling to One File:

Bundling to One File
~~~~~~~~~~~~~~~~~~~~~

|PyInstaller| can bundle your script and all its dependencies into a single
executable named :file:`myscript` (:file:`myscript.exe` in Windows).

The advantage is that your users get something they understand,
a single executable to launch.
A disadvantage is that any related files
such as a README must be distributed separately.
Also, the single executable is a little slower to start up than
the one-folder bundle.

Before you attempt to bundle to one file, make sure your app
works correctly when bundled to one folder.
It is is *much* easier to diagnose problems in one-folder mode.

.. _how the one-file program works:

How the One-File Program Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The |bootloader| is the heart of the one-file bundle also.
When started it creates a temporary folder
in the appropriate temp-folder location for this OS.
The folder is named :file:`_MEI{xxxxxx}`, where *xxxxxx* is a random number.

The one executable file contains an embedded archive of all the Python
modules used by your script, as well as
compressed copies of any non-Python support files (e.g. ``.so`` files).
The |bootloader| uncompresses the support files and writes copies
into the the temporary folder.
This can take a little time.
That is why a one-file app is a little slower to start
than a one-folder app.

After creating the temporary folder, the |bootloader|
proceeds exactly as for the one-folder bundle,
in the context of the temporary folder.
When the bundled code terminates,
the |bootloader| deletes the temporary folder.

(In Linux and related systems, it is possible
to mount the ``/tmp`` folder with a "no-execution" option.
That option is not compatible with a |PyInstaller|
one-file bundle. It needs to execute code out of :file:`/tmp`.)

Because the program makes a temporary folder with a unique name,
you can run multiple copies of the app;
they won't interfere with each other.
However, running multiple copies is expensive in disk space because
nothing is shared.

The :file:`_MEI{xxxxxx}` folder is not removed if the program crashes
or is killed (kill -9 on Unix, killed by the Task Manager on Windows,
"Force Quit" on Mac OS).
Thus if your app crashes frequently, your users will lose disk space to
multiple :file:`_MEI{xxxxxx}` temporary folders.

It is possible to control the location of the :file:`_MEI{xxxxxx}` folder by
using the ``--runtime-tmpdir`` command line option. The specified path is
stored in the executable, and the bootloader will create the
:file:`_MEI{xxxxxx}` folder inside of the specified folder. Please see
:ref:`defining the extraction location` for details.

.. Note::

    Do *not* give administrator privileges to a one-file executable
    (setuid root in Unix/Linux, or the "Run this program as an administrator"
    property in Windows 7).
    There is an unlikely but not impossible way in which a malicious attacker could
    corrupt one of the shared libraries in the temp folder
    while the |bootloader| is preparing it.
    Distribute a privileged program in one-folder mode instead.

.. Note::
    Applications that use `os.setuid()` may encounter permissions errors.
    The temporary folder where the bundled app runs may not being readable
    after `setuid` is called. If your script needs to
    call `setuid`, it may be better to use one-folder mode
    so as to have more control over the permissions on its files. 


Using a Console Window
~~~~~~~~~~~~~~~~~~~~~~~

By default the |bootloader| creates a command-line console
(a terminal window in Linux and Mac OS, a command window in Windows).
It gives this window to the Python interpreter for its standard input and output.
Your script's use of ``print`` and ``input()`` are directed here.
Error messages from Python and default logging output
also appear in the console window.

An option for Windows and Mac OS is to tell |PyInstaller| to not provide a console window.
The |bootloader| starts Python with no target for standard output or input.
Do this when your script has a graphical interface for user input and can properly
report its own diagnostics.


Hiding the Source Code
~~~~~~~~~~~~~~~~~~~~~~~~

The bundled app does not include any source code.
However, |PyInstaller| bundles compiled Python scripts (``.pyc`` files).
These could in principle be decompiled to reveal the logic of
your code.

If you want to hide your source code more thoroughly, one possible option
is to compile some of your modules with Cython_.
Using Cython you can convert Python modules into C and compile
the C to machine language.
|PyInstaller| can follow import statements that refer to
Cython C object modules and bundle them.

Additionally, Python bytecode can be obfuscated with AES256 by specifying
an encryption key on PyInstaller's command line. Please note that it is still
very easy to extract the key and get back the original bytecode, but it
should prevent most forms of "casual" tampering.
See :ref:`encrypting python bytecode` for details.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
