.. _using pyinstaller:

====================
Using PyInstaller
====================


The syntax of the ``pyinstaller`` command is:

    ``pyinstaller`` [*options*] *script* [*script* ...] | *specfile*

In the most simple case,
set the current directory to the location of your program ``myscript.py``
and execute::

    pyinstaller myscript.py

PyInstaller analyzes :file:`myscript.py` and:

* Writes :file:`myscript.spec` in the same folder as the script.
* Creates a folder :file:`build` in the same folder as the script if it does not exist.
* Writes some log files and working files in the ``build`` folder.
* Creates a folder :file:`dist` in the same folder as the script if it does not exist.
* Writes the :file:`myscript` executable folder in the :file:`dist` folder.

In the :file:`dist` folder you find the bundled app you distribute to your users.

Normally you name one script on the command line.
If you name more, all are analyzed and included in the output.
However, the first script named supplies the name for the
spec file and for the executable folder or file.
Its code is the first to execute at run-time.

For certain uses you may edit the contents of ``myscript.spec``
(described under :ref:`Using Spec Files`).
After you do this, you name the spec file to PyInstaller instead of the script:

    ``pyinstaller myscript.spec``

The :file:`myscript.spec` file contains most of the information
provided by the options that were specified when
:command:`pyinstaller` (or :command:`pyi-makespec`)
was run with the script file as the argument.
You typically do not need to specify any options when running
:command:`pyinstaller` with the spec file.
Only :ref:`a few command-line options <Using Spec Files>`
have an effect when building from a spec file.

You may give a path to the script or spec file, for example

    ``pyinstaller`` `options...` ``~/myproject/source/myscript.py``

or, on Windows,

    ``pyinstaller "C:\Documents and Settings\project\myscript.spec"``


Options
~~~~~~~~~~~~~~~

A full list of the ``pyinstaller`` command's options are as follows:

.. include:: _pyinstaller-options.tmp


Shortening the Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because of its numerous options, a full ``pyinstaller`` command
can become very long.
You will run the same command again and again as you develop
your script.
You can put the command in a shell script or batch file,
using line continuations to make it readable.
For example, in GNU/Linux::

    pyinstaller --noconfirm --log-level=WARN \
        --onefile --nowindow \
        --add-data="README:." \
        --add-data="image1.png:img" \
        --add-binary="libfoo.so:lib" \
        --hidden-import=secret1 \
        --hidden-import=secret2 \
        --upx-dir=/usr/local/share/ \
        myscript.spec

Or in Windows, use the little-known BAT file line continuation::

    pyinstaller --noconfirm --log-level=WARN ^
        --onefile --nowindow ^
        --add-data="README:." ^
        --add-data="image1.png:img" ^
        --add-binary="libfoo.so:lib" ^
        --hidden-import=secret1 ^
        --hidden-import=secret2 ^
        --icon=..\MLNMFLCN.ICO ^
        myscript.spec


Running PyInstaller from Python code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to run PyInstaller from Python code, you can use the ``run`` function
defined in ``PyInstaller.__main__``. For instance, the following code:

.. code-block:: python

    import PyInstaller.__main__

    PyInstaller.__main__.run([
        'my_script.py',
        '--onefile',
        '--windowed'
    ])

Is equivalent to:

.. code-block:: shell

    pyinstaller my_script.py --onefile --windowed


Using UPX
~~~~~~~~~~~~~~~~~~~

UPX_ is a free utility for compressing executable files and libraries.
It is available for most operating systems and can compress a large number
of executable file formats. See the UPX_ home page for downloads, and for
the list of supported file formats.

When UPX is available, PyInstaller uses it to individually compress
each collected binary file (executable, shared library, or python
extension) in order to reduce the overall size of the frozen application
(the one-dir bundle directory, or the one-file executable). The frozen
application's executable itself is not UPX-compressed (regardless of one-dir
or one-file mode), as most of its size comprises the embedded archive that
already contains individually compressed files.

PyInstaller looks for the UPX in the standard executable path(s) (defined
by ``PATH`` environment variable), or in the path specified via the
:option:`--upx-dir` command-line option. If found, it is used automatically.
The use of UPX can be completely disabled using the :option:`--noupx`
command-line option.

.. note::
    UPX is currently used only on Windows. On other operating systems,
    the collected binaries are not processed even if UPX is found. The
    shared libraries (e.g., the Python shared library) built on modern
    linux distributions seem to break when processed with UPX, resulting
    in defunct application bundles. On macOS, UPX currently fails to
    process .dylib shared libraries; furthermore the UPX-compressed files
    fail the validation check of the ``codesign`` utility, and therefore
    cannot be code-signed (which is a requirement on the Apple M1 platform).


Excluding problematic files from UPX processing
-----------------------------------------------

Using UPX may end up corrupting a collected shared library. Known examples
of such corruption are Windows DLLs with `Control Flow Guard (CFG) enabled
<https://github.com/upx/upx/issues/398>`_, as well as `Qt5 and Qt6
plugins <https://github.com/upx/upx/issues/107>`_. In such cases,
individual files may be need to be excluded from UPX processing, using
the :option:`--upx-exclude` option (or using the ``upx_exclude`` argument
in the :ref:`.spec file <using spec files>`).

.. versionchanged:: 4.2
    PyInstaller detects CFG-enabled DLLs and automatically excludes
    them from UPX processing.

.. versionchanged:: 4.3
    PyInstaller automatically excludes Qt5 and Qt6 plugins from
    UPX processing.

Although PyInstaller attempts to automatically detect and exclude some of
the problematic files from UPX processing, there are cases where the
UPX excludes need to be specified manually. For example, 32-bit Windows
binaries from the ``PySide2`` package (Qt5 DLLs and python extension modules)
have been `reported <https://github.com/pyinstaller/pyinstaller/issues/4178#issuecomment-868985789>`_
to be corrupted by UPX.

.. versionchanged:: 5.0
    Unlike earlier releases that compared the provided UPX-exclude names
    against basenames of the collect binary files (and, due to incomplete
    case normalization, required provided exclude names to be lowercase
    on Windows), the UPX-exclude pattern matching now uses OS-default
    case sensitivity and supports the wildcard (``*``) operator. It also
    supports specifying (full or partial) parent path of the file.

The provided UPX exclude patterns are matched against *source* (origin)
paths of the collected binary files, and the matching is performed from
right to left.

For example, to exclude Qt5 DLLs from the PySide2 package, use
``--upx-exclude "Qt*.dll"``, and to exclude the python extensions
from the PySide2 package, use ``--upx-exclude "PySide2\*.pyd"``.


.. _splash screen:

Splash Screen *(Experimental)*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. Note::
    This feature is incompatible with macOS. In the current design, the
    splash screen operates in a secondary thread, which is disallowed by
    the Tcl/Tk (or rather, the underlying GUI toolkit) on macOS.

Some applications may require a splash screen as soon as the application
(bootloader) has been started, because especially in onefile mode large
applications may have long extraction/startup times, while the bootloader
prepares everything, where the user cannot judge whether the application
was started successfully or not.

The bootloader is able to display a one-image (i.e. only an image) splash
screen, which is displayed before the actual main extraction process starts.
The splash screen supports non-transparent and hard-cut-transparent images as background
image, so non-rectangular splash screens can also be displayed.

.. Note::
    Splash images with transparent regions are not supported on Linux due to
    Tcl/Tk platform limitations. The ``-transparentcolor`` and ``-transparent`` wm attributes
    used by PyInstaller are not available to Linux.

This splash screen is based on `Tcl/Tk`_, which is the same library used by the Python
module `tkinter`_. PyInstaller bundles the dynamic libraries of tcl and tk into the
application at compile time. These are loaded into the bootloader at startup of the
application after they have been extracted (if the program has been packaged as an
onefile archive). Since the file sizes of the necessary dynamic libraries are very small,
there is almost no delay between the start of the application and the splash screen.
The compressed size of the files necessary for the splash screen is about *1.5 MB*.

As an additional feature, text can optionally be displayed on the splash screen. This
can be changed/updated from within Python. This offers the possibility to
display the splash screen during longer startup procedures of a Python program
(e.g. waiting for a network response or loading large files into memory). You
can also start a GUI behind the splash screen, and only after it is completely
initialized the splash screen can be closed. Optionally, the font, color and
size of the text can be set. However, the font must be installed on the user
system, as it is not bundled. If the font is not available, a fallback font is used.

If the splash screen is configured to show text, it will automatically (as onefile archive)
display the name of the file that is currently being unpacked, this acts as a progress bar.


The ``pyi_splash`` Module
~~~~~~~~~~~~~~~~~~~~~~~~~

The splash screen is controlled from within Python by the :mod:`pyi_splash` module, which can
be imported at runtime. This module **cannot** be installed by a package manager
because it is part of PyInstaller and is included as needed.
This module must be imported within the Python program. The usage is as follows::

    import pyi_splash

    # Update the text on the splash screen
    pyi_splash.update_text("PyInstaller is a great software!")
    pyi_splash.update_text("Second time's a charm!")

    # Close the splash screen. It does not matter when the call
    # to this function is made, the splash screen remains open until
    # this function is called or the Python program is terminated.
    pyi_splash.close()

Of course the import should be in a ``try ... except`` block, in case the program is
used externally as a normal Python script, without a bootloader.
For a detailed description see :ref:`pyi_splash Module`.


.. _defining the extraction location:

Defining the Extraction Location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When building your application in ``onefile`` mode (see :ref:`Bundling to
One File` and :ref:`how the one-file program works`), you might encounter
situations where you want to control the location of the temporary directory
where the application unpacks itself. For example:

- your application is supposed to be running for long periods of time,
  and you need to prevent its files from being deleted by the OS that
  performs periodic clean-up in standard temporary directories.

- your target POSIX system does not use standard temporary directory
  location (i.e., ``/tmp``) and the standard environment variables for
  temporary directory are not set in the environment.

- the default temporary directory on the target POSIX system is mounted
  with ``noexec`` option, which prevents the frozen application from
  loading the unpacked shared libraries.

The location of the temporary directory can be overridden dynamically,
by setting corresponding environment variable(s) before launching the
application, or set statically, using the :option:`--runtime-tmpdir` option
during the build process.

Using environment variables
---------------------------

The extraction location can be controlled dynamically, by setting the
environment variable(s) that PyInstaller uses to determine the temporary
directory. This can, for example, be done in a wrapper shell script that
sets the environment variable(s) before running the frozen application's
executable.

On POSIX systems, the environment variables used for temporary
directory location are ``TMPDIR``, ``TEMP``, and ``TMP``, in that
order; if none are defined (or the corresponding directories do not
exist or cannot be used), ``/tmp``, ``/var/tmp``, and ``/usr/tmp`` are
used as hard-coded fall-backs, in the specified order. The directory
specified via the environment variable must exist (i.e., the application
attempts to create only its own directory under the base temporary directory).

On Windows, the default temporary directory location is determined via
`GetTempPathW <https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-gettemppathw>`_
function (which looks at ``TMP`` and ``TEMP`` environment variables for
initial temporary directory candidates).

Using the :option:`--runtime-tmpdir` option
-------------------------------------------

The location of the temporary directory can be set statically, at compile
time, using the :option:`--runtime-tmpdir` option. If this option is used,
the bootloader will ignore temporary directory locations defined by
the OS, and use the specified path. The path can be either absolute
or relative (which makes it relative to the current working directory).

Please use this option only if you know what you are doing.

.. note::
    On POSIX systems, PyInstaller's bootloader does **not** perform shell-style
    environment variable expansion on the path string given via
    :option:`--runtime-tmpdir` option. Therefore, using environment
    variables (e.g., ``~`` or ``$HOME``) in the path will **not** work.


.. _supporting multiple platforms:

Supporting Multiple Platforms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you distribute your application for only one combination of OS and Python,
just install PyInstaller like any other package and use it in your
normal development setup.


Supporting Multiple Python Environments
-----------------------------------------

When you need to bundle your application within one OS
but for different versions of Python and support libraries -- for example,
a Python 3.6 version and a Python 3.7 version;
or a supported version that uses Qt4 and a development version that uses Qt5 --
we recommend you use venv_.
With `venv` you can maintain different combinations of Python
and installed packages, and switch from one combination to another easily.
These are called `virtual environments` or `venvs` in short.

* Use `venv` to create as many different development environments as you need,
  each with its unique combination of Python and installed packages.
* Install PyInstaller in each virtual environment.
* Use PyInstaller to build your application in each virtual environment.

Note that when using `venv`, the path to the PyInstaller commands is:

* Windows: ENV_ROOT\\Scripts
* Others:  ENV_ROOT/bin

Under Windows, the pip-Win_ package makes it
especially easy to set up different environments and switch between them.
Under GNU/Linux and macOS, you switch environments at the command line.

See :pep:`405`
and the official `Python Tutorial on Virtual Environments and Packages
<https://docs.python.org/3/tutorial/venv.html>`_
for more information about Python virtual environments.


Supporting Multiple Operating Systems
---------------------------------------

If you need to distribute your application for more than one OS,
for example both Windows and macOS, you must install PyInstaller
on each platform and bundle your app separately on each.

You can do this from a single machine using virtualization.
The free virtualBox_ or the paid VMWare_ and Parallels_
allow you to run another complete operating system as a "guest".
You set up a virtual machine for each "guest" OS.
In it you install
Python, the support packages your application needs, and PyInstaller.

A `File Sync & Share`__ system like NextCloud_ is useful with virtual machines.
Install the synchronization client in each virtual machine,
all linked to your synchronization account.
Keep a single copy of your script(s) in a synchronized folder.
Then on any virtual machine you can run PyInstaller thus::

    cd ~/NextCloud/project_folder/src # GNU/Linux, Mac -- Windows similar
    rm *.pyc # get rid of modules compiled by another Python
    pyinstaller --workpath=path-to-local-temp-folder  \
                --distpath=path-to-local-dist-folder  \
                ...other options as required...       \
                ./myscript.py

__ https://en.wikipedia.org/wiki/Enterprise_file_synchronization_and_sharing

PyInstaller reads scripts from the common synchronized folder,
but writes its work files and the bundled app in folders that
are local to the virtual machine.

If you share the same home directory on multiple platforms, for
example GNU/Linux and macOS, you will need to set the PYINSTALLER_CONFIG_DIR
environment variable to different values on each platform otherwise
PyInstaller may cache files for one platform and use them on the other
platform, as by default it uses a subdirectory of your home directory
as its cache location.

It is said to be possible to cross-develop for Windows under GNU/Linux
using the free Wine_ environment.
Further details are needed, see `How to Contribute`_.


.. _capturing windows version data:

Capturing Windows Version Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Windows app may require a Version resource file.
A Version resource contains a group of data structures,
some containing binary integers and some containing strings,
that describe the properties of the executable.
For details see the Microsoft `Version Information Structures`_ page.

Version resources are complex and
some elements are optional, others required.
When you view the version tab of a Properties dialog,
there's no simple relationship between
the data displayed and the structure of the resource.
For this reason PyInstaller includes the ``pyi-grab_version`` command.
It is invoked with the full path name of any Windows executable
that has a Version resource:

      ``pyi-grab_version`` *executable_with_version_resource*

The command writes text that represents
a Version resource in readable form to standard output.
You can copy it from the console window or redirect it to a file.
Then you can edit the version information to adapt it to your program.
Using ``pyi-grab_version`` you can find an executable that displays the kind of
information you want, copy its resource data, and modify it to suit your package.

The version text file is encoded UTF-8 and may contain non-ASCII characters.
(Unicode characters are allowed in Version resource string fields.)
Be sure to edit and save the text file in UTF-8 unless you are
certain it contains only ASCII string values.

Your edited version text file can be given with the :option:`--version-file`
option to ``pyinstaller`` or ``pyi-makespec``.
The text data is converted to a Version resource and
installed in the bundled app.

In a Version resource there are two 64-bit binary values,
``FileVersion`` and ``ProductVersion``.
In the version text file these are given as four-element tuples,
for example::

    filevers=(2, 0, 4, 0),
    prodvers=(2, 0, 4, 0),

The elements of each tuple represent 16-bit values
from most-significant to least-significant.
For example the value ``(2, 0, 4, 0)`` resolves to
``0002000000040000`` in hex.

You can also install a Version resource from a text file after
the bundled app has been created, using the ``pyi-set_version`` command:

    ``pyi-set_version`` *version_text_file* *executable_file*

The ``pyi-set_version`` utility reads a version text file as written
by ``pyi-grab_version``, converts it to a Version resource,
and installs that resource in the *executable_file* specified.

For advanced uses, examine a version text file as written by  ``pyi-grab_version``.
You find it is Python code that creates a ``VSVersionInfo`` object.
The class definition for ``VSVersionInfo`` is found in
``utils/win32/versioninfo.py`` in the PyInstaller distribution folder.
You can write a program that imports ``versioninfo``.
In that program you can ``eval``
the contents of a version info text file to produce a
``VSVersionInfo`` object.
You can use the ``.toRaw()`` method of that object to
produce a Version resource in binary form.
Or you can apply the ``unicode()`` function to the object
to reproduce the version text file.


.. _macOS app bundles:

Building macOS App Bundles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Under macOS, PyInstaller always builds a UNIX executable in
:file:`dist`.
If you specify :option:`--onedir`, the output is a folder named :file:`myscript`
containing supporting files and an executable named :file:`myscript`.
If you specify :option:`--onefile`, the output is a single UNIX executable
named :file:`myscript`.
Either executable can be started from a Terminal command line.
Standard input and output work as normal through that Terminal window.

If you specify :option:`--windowed` with either option, the ``dist`` folder
also contains a macOS app bundle named :file:`myscript.app`.

.. note::
    Generating app bundles with onefile executables (i.e., using the
    combination of :option:`--onefile` and :option:`--windowed` options),
    while possible, is not recommended. Such app bundles are inefficient,
    because they require unpacking on each run (and the unpacked content
    might be scanned by the OS each time). Furthermore, onefile executables
    will not work when signed/notarized with sandbox enabled (which
    is a requirement for distribution of apps through Mac App Store).

As you are likely aware, an app bundle is a special type of folder.
The one built by PyInstaller always contains a folder named
:file:`Contents`, which contains:

  + A file named :file:`Info.plist` that describes the app.
  + A folder named :file:`MacOS` that contains the program executable.
  + A folder named :file:`Frameworks` that contains the collected binaries
    (shared libraries, python extensions) and nested .framework bundles.
    It also contains symbolic links to data files and directories from
    the :file:`Resources` directory.
  + A folder named :file:`Resources` that contains the icon file and all
    collected data files. It also contains symbolic links to binaries
    and directories from the :file:`Resources` directory.

.. note::
    The contents of the :file:`Frameworks` and :file:`Resources` directories
    are cross-linked between the two directories in an effort to
    maintain an illusion of a single content directory (which is required
    by some packages), while also trying to satisfy the Apple's file
    placement requirements for codesigning.

Use the :option:`--icon` argument to specify a custom icon for the application.
It will be copied into the :file:`Resources` folder.
(If you do not specify an icon file, PyInstaller supplies a
file :file:`icon-windowed.icns` with the PyInstaller logo.)

Use the :option:`--osx-bundle-identifier` argument to add a bundle identifier.
This becomes the ``CFBundleIdentifier`` used in code-signing
(see the `PyInstaller code signing recipe`_
and for more detail, the `Apple code signing overview`_ technical note).

You can add other items to the :file:`Info.plist` by editing the spec file;
see :ref:`Spec File Options for a macOS Bundle` below.


Platform-specific Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~

GNU/Linux
-------------------

Making GNU/Linux Apps Forward-Compatible
==========================================

Under GNU/Linux, PyInstaller does not bundle ``libc``
(the C standard library, usually ``glibc``, the Gnu version) with the app.
Instead, the app expects to link dynamically to the ``libc`` from the
local OS where it runs.
The interface between any app and ``libc`` is forward compatible to
newer releases, but it is not backward compatible to older releases.

For this reason, if you bundle your app on the current version of GNU/Linux,
it may fail to execute (typically with a runtime dynamic link error) if
it is executed on an older version of GNU/Linux.

The solution is to always build your app on the *oldest* version of
GNU/Linux you mean to support.
It should continue to work with the ``libc`` found on newer versions.

The GNU/Linux standard libraries such as ``glibc`` are distributed in 64-bit
and 32-bit versions, and these are not compatible.
As a result you cannot bundle your app on a 32-bit system and run it
on a 64-bit installation, nor vice-versa.
You must make a unique version of the app for each word-length supported.

Note that PyInstaller does bundle other shared libraries that are discovered
via dependency analysis, such as libstdc++.so.6, libfontconfig.so.1,
libfreetype.so.6. These libraries may be required on systems where older
(and thus incompatible) versions of these libraries are available. On the
other hand, the bundled libraries may cause issues when trying to load a
system-provided shared library that is linked against a newer version of the
system-provided library.

For example, system-installed mesa DRI drivers (e.g., radeonsi_dri.so)
depend on the system-provided version of libstdc++.so.6. If the frozen
application bundles an older version of libstdc++.so.6 (as collected from
the build system), this will likely cause missing symbol errors and prevent
the DRI drivers from loading. In this case, the bundled libstdc++.so.6
should be removed. However, this may not work on a different distribution
that provides libstdc++.so.6 older than the one from the build system; in
that case, the bundled version should be kept, because the system-provided
version may lack the symbols required by other collected binaries that depend
on libstdc++.so.6.

.. _Platform-specific Notes - Windows:

Windows
---------------

The developer needs to take
special care to include the Visual C++ run-time .dlls:
Python 3.5+ uses Visual Studio 2015 run-time, which has been renamed into
`“Universal CRT“
<https://blogs.msdn.microsoft.com/vcblog/2015/03/03/introducing-the-universal-crt/>`_
and has become part of Windows 10.
For Windows Vista through Windows 8.1 there are Windows Update packages,
which may or may not be installed in the target-system.
So you have the following options:

1. Build on *Windows 7* which has been reported to work.

2. Include one of the VCRedist packages (the redistributable package files)
   into your application's installer. This is Microsoft's recommended way, see
   “Distributing Software that uses the Universal CRT“ in the above-mentioned
   link, numbers 2 and 3.

3. Install the `Windows Software Development Kit (SDK) for Windows 10
   <https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk>`_ and expand the
   `.spec`-file to include the required DLLs, see “Distributing Software that
   uses the Universal CRT“ in the above-mentioned link, number 6.

   If you think, PyInstaller should do this by itself, please :ref:`help
   improving <how-to-contribute>` PyInstaller.



macOS
-------------------

Making macOS apps Forward-Compatible
=====================================

On macOS, system components from one version of the OS are usually compatible
with later versions, but they may not work with earlier versions. While
PyInstaller does not collect system components of the OS, the collected
3rd party binaries (e.g., python extension modules) are built against
specific version of the OS libraries, and may or may not support older
OS versions.

As such, the only way to ensure that your frozen application supports
an older version of the OS is to freeze it on the oldest version of the
OS that you wish to support. This applies especially when building with
`Homebrew`_ python, as its binaries usually explicitly target the
running OS.

For example, to ensure compatibility with "Mojave" (10.14) and later versions,
you should set up a full environment (i.e., install python, PyInstaller,
your application's code, and all its dependencies) in a copy of macOS 10.14,
using a virtual machine if necessary. Then use PyInstaller to freeze
your application in that environment; the generated frozen application
should be compatible with that and later versions of macOS.


Building 32-bit Apps in macOS
================================

.. note:: This section is largely obsolete, as support for 32-bit application
          was removed in macOS 10.15 Catalina (for 64-bit multi-arch support
          on modern versions of macOS, see :ref:`here <macos multi-arch support>`).
          However, PyInstaller still supports building 32-bit bootloader,
          and 32-bit/64-bit Python installers are still available from
          python.org for (some) versions of Python 3.7 which PyInstaller dropped
          support for in v6.0.

Older versions of macOS supported both 32-bit and 64-bit executables.
PyInstaller builds an app using the the word-length of the Python used to execute it.
That will typically be a 64-bit version of Python,
resulting in a 64-bit executable.
To create a 32-bit executable, run PyInstaller under a 32-bit Python.

To verify that the installed python version supports execution in either
64- or 32-bit mode, use the ``file`` command on the Python executable::

    $ file /usr/local/bin/python3
    /usr/local/bin/python3: Mach-O universal binary with 2 architectures
    /usr/local/bin/python3 (for architecture i386):     Mach-O executable i386
    /usr/local/bin/python3 (for architecture x86_64):   Mach-O 64-bit executable x86_64

The OS chooses which architecture to run, and typically defaults to 64-bit.
You can force the use of either architecture by name using the ``arch`` command::

    $ /usr/local/bin/python3
    Python 3.7.6 (v3.7.6:43364a7ae0, Dec 18 2019, 14:12:53)
    [GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import sys; sys.maxsize
    9223372036854775807

    $ arch -i386 /usr/local/bin/python3
    Python 3.7.6 (v3.7.6:43364a7ae0, Dec 18 2019, 14:12:53)
    [GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import sys; sys.maxsize
    2147483647

.. note:: PyInstaller does not provide pre-built 32-bit bootloaders for
          macOS anymore. In order to use PyInstaller with 32-bit python,
          you need to :ref:`build the bootloader <building the bootloader>`
          yourself, using an XCode
          version that still supports compiling 32-bit. Depending on the
          compiler/toolchain, you may also need to explicitly pass
          ``--target-arch=32bit`` to the ``waf`` command.


Getting the Opened Document Names
=================================

When user double-clicks a document of a type that is registered with
your application, or when a user drags a document and drops it
on your application's icon, macOS launches your application
and provides the name(s) of the opened document(s) in the
form of an OpenDocument AppleEvent.

These events are typically handled via installed event handlers in your
application (e.g., using ``Carbon`` API via ``ctypes``, or using
facilities provided by UI toolkits, such as ``tkinter`` or ``PyQt5``).

Alternatively, PyInstaller also supports conversion of open
document/URL events into arguments that are appended to :data:`sys.argv`.
This applies only to events received during application launch, i.e.,
before your frozen code is started. To handle events that are dispatched
while your application is already running, you need to set up corresponding
event handlers.

For details, see :ref:`this section <macos event forwarding and argv emulation>`.


AIX
----------------------

Depending on whether Python was build as a 32-bit or a 64-bit executable
you may need to set or unset
the environment variable :envvar:`OBJECT_MODE`.
To determine the size the following command can be used::

    $ python -c "import sys; print(sys.maxsize <= 2**32)"
    True

When the answer is ``True`` (as above) Python was build as a 32-bit
executable.

When working with a 32-bit Python executable proceed as follows::

    $ unset OBJECT_MODE
    $ pyinstaller <your arguments>

When working with a 64-bit Python executable proceed as follows::

    $ export OBJECT_MODE=64
    $ pyinstaller <your arguments>


.. _Platform-specific Notes - Cygwin:

Cygwin
------

Cygwin-based Frozen Applications and ``cygwin1.dll``
====================================================

Under Cygwin, the PyInstaller's bootloader executable (and therefore the
frozen application's executable) ends up being dynamically linked against
the ``cygwin1.dll``. As noted under `Q 6.14 of the Cygwin's FAQ
<https://www.cygwin.com/faq.html#faq.programming.static-linking>`_,
the Cygwin library cannot be statically linked into an executable in
order to obtain an independent, self-contained executable.

This means that at run-time, the ``cygwin1.dll`` needs to be available
to the frozen application's executable for it to be able to launch.
Depending on the deployment scenario, this means that it needs to be
either available in the environment (i.e., the environment's search path)
or a copy of the DLL needs to be available *next to the executable*.

On the other hand, Cygwin does not permit more than one copy of
``cygwin1.dll``; or rather, it requires multiple copies of the DLL
to be strictly separated, as each instance constitutes its own Cygwin
installation/environment (see `Q 4.20 of the Cygwin FAQ
<https://www.cygwin.com/faq.html#faq.using.multiple-copies>`_).
Trying to run an executable with an adjacent copy of the DLL from an
existing Cygwin environment will likely result in the application crashing.

In practice, this means that if you want to create a frozen application
that will run in an existing Cygwin environment, the application
should not bundle a copy of ``cygwin1.dll``. On the other hand, if you
want to create a frozen application that will run outside of a Cygwin
environment (i.e., a "stand-alone" application that runs directly under
Windows), the application will require a copy of ``cygwin1.dll`` -- and
that copy needs to be placed *next to the program's executable*, regardless
of whether ``onedir`` or ``onefile`` build mode is used.

As PyInstaller cannot guess the deployment mode that you are pursuing,
it makes no attempt to collect ``cygwin1.dll``. So if you want your
application to run outside of an externally-provided Cygwin environment,
you need to place a copy of ``cygwin1.dll`` next to the program's
executable and distribute them together.

.. note::
    If you plan to create a "stand-alone" Cygwin-based frozen application
    (i.e., distribute ``cygwin1.dll`` along with the executable), you will
    likely want to build the bootloader with statically linked ``zlib``
    library, in order to avoid a run-time dependency on ``cygz.dll``.

    You can do so by passing ``--static-zlib`` option to ``waf`` when
    manually building the bootloader before installing PyInstaller
    from source, or by adding the option to ``PYINSTALLER_BOOTLOADER_WAF_ARGS``
    environment variable if installing directly via ``pip install``.
    For details, see :ref:`building the bootloader`.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
