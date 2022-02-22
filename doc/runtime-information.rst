.. _run-time information:

Run-time Information
=====================

Your app should run in a bundle exactly as it does when run from source.
However, you may want to learn at run-time whether the app is running from
source or whether it is bundled ("frozen"). You can use the following code to
check "are we bundled?"::

    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print('running in a PyInstaller bundle')
    else:
        print('running in a normal Python process')

When a bundled app starts up, the |bootloader| sets the ``sys.frozen``
attribute and stores the absolute path to the bundle folder in
``sys._MEIPASS``. For a one-folder bundle, this is the path to that folder. For
a one-file bundle, this is the path to the temporary folder created by the
|bootloader| (see :ref:`How the One-File Program Works`).

When your app is running, it may need to access data files in one of the
following locations:

* Files that were bundled with it (see :ref:`Adding Data Files`).
* Files the user has placed with the app bundle, say in the same folder.
* Files in the user's current working directory.

The program has access to several variables for these uses.


Using ``__file__``
~~~~~~~~~~~~~~~~~~

When your program is not bundled, the Python variable ``__file__`` refers to
the current path of the module it is contained in. When importing a module
from a bundled script, the |PyInstaller| |bootloader| will set the module's
``__file__`` attribute to the correct path relative to the bundle folder.

For example, if you import ``mypackage.mymodule`` from a bundled script, then
the ``__file__`` attribute of that module will be ``sys._MEIPASS +
'mypackage/mymodule.pyc'``.  So if you have a data file at
``mypackage/file.dat`` that you added to the bundle at ``mypackage/file.dat``,
the following code will get its path (in both the non-bundled and the bundled
case)::

    from os import path
    path_to_dat = path.abspath(path.join(path.dirname(__file__), 'file.dat'))

In the main script (the ``__main__`` module) itself, the ``__file__``
variable contains path to the script file. In Python 3.8 and earlier,
this path is either absolute or relative (depending on how the script
was passed to the ``python`` interpreter), while in Python 3.9 and later,
it is always an absolute path. In the bundled script, the |PyInstaller|
|bootloader| always sets the ``__file__`` variable inside the ``__main__``
module to the absolute path inside the bundle directory, as if the
byte-compiled entry-point script existed there.

For example, if your entry-point script is called ``program.py``, then
the ``__file__`` attribute inside the bundled script will point to
``sys._MEIPASS + 'program.py'``. Therefore, locating a data file relative
to the main script can be either done directly using ``sys._MEIPASS`` or
via the parent path of the ``__file__`` inside the main script.

The following example will get the path to a file ``other-file.dat``
located next to the main script if not bundled and inside the bundle folder
if it is bundled::

    from os import path
    bundle_dir = path.abspath(path.dirname(__file__))
    path_to_dat = path.join(bundle_dir, 'other-file.dat')

Or, if you'd rather use pathlib_::

    from pathlib import Path
    path_to_dat = Path(__file__).resolve().with_name("other-file.dat")

.. versionchanged:: 4.3

    Formerly, the ``__file__`` attribute of the entry-point script
    (the ``__main__`` module) was set to only its basename rather than
    its full (absolute or relative) path within the bundle directory.
    Therefore, |PyInstaller| documentation used to suggest ``sys._MEIPASS``
    as means for locating resources relative to the bundled entry-point
    script. Now, ``__file__`` is always set to the absolute full path,
    and is the preferred way of locating such resources.


Placing data files at expected locations inside the bundle
----------------------------------------------------------

To place the data-files where your code expects them to be (i.e., relative
to the main script or bundle directory), you can use the **dest** parameter
of the :option:`--add-data=source:dest <--add-data>` command-line switches.
Assuming you normally
use the following code in a file named ``my_script.py`` to locate a file
``file.dat`` in the same folder::

    from os import path
    path_to_dat = path.abspath(path.join(path.dirname(__file__), 'file.dat'))

Or the pathlib_ equivalent::

    from pathlib import Path
    path_to_dat = Path(__file__).resolve().with_name("file.dat")

And ``my_script.py`` is **not** part of a package (not in a folder containing
an ``__init_.py``), then ``__file__`` will be ``[app root]/my_script.pyc``
meaning that if you put ``file.dat`` in the root of your package, using::

    PyInstaller --add-data=/path/to/file.dat:.

It will be found correctly at runtime without changing ``my_script.py``.

.. note:: Windows users should use ``;`` instead of ``:`` in the above line.

If ``__file__`` is checked from inside a package or library (say
``my_library.data``) then ``__file__`` will be
``[app root]/my_library/data.pyc`` and :option:`--add-data` should mirror that::

    PyInstaller --add-data=/path/to/my_library/file.dat:./my_library

However, in this case it is much easier to switch to :ref:`the spec file
<Using Spec Files>` and use the
:func:`PyInstaller.utils.hooks.collect_data_files` helper function::

    from PyInstaller.utils.hooks import collect_data_files

    a = Analysis(...,
                 datas=collect_data_files("my_library"),
                 ...)

Using ``sys.executable`` and ``sys.argv[0]``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a normal Python script runs, ``sys.executable`` is the path to the
program that was executed, namely, the Python interpreter.
In a frozen app, ``sys.executable`` is also the path to the
program that was executed, but that is not Python;
it is the bootloader in either the one-file app
or the executable in the one-folder app.
This gives you a reliable way to locate the frozen executable the user
actually launched.

The value of ``sys.argv[0]`` is the name or relative path that was
used in the user's command.
It may be a relative path or an absolute path depending
on the platform and how the app was launched.

If the user launches the app by way of a symbolic link,
``sys.argv[0]`` uses that symbolic name,
while ``sys.executable`` is the actual path to the executable.
Sometimes the same app is linked under different names
and is expected to behave differently depending on the name that is
used to launch it.
For this case, you would test ``os.path.basename(sys.argv[0])``

On the other hand, sometimes the user is told to store the executable
in the same folder as the files it will operate on,
for example a music player that should be stored in the same folder
as the audio files it will play.
For this case, you would use ``os.path.dirname(sys.executable)``.

The following small program explores some of these possibilities.
Save it as ``directories.py``.
Execute it as a Python script,
then bundled as a one-folder app.
Then bundle it as a one-file app and launch it directly and also via a
symbolic link::

	#!/usr/bin/env python3
	import sys, os
	frozen = 'not'
	if getattr(sys, 'frozen', False):
		# we are running in a bundle
		frozen = 'ever so'
		bundle_dir = sys._MEIPASS
	else:
		# we are running in a normal Python environment
		bundle_dir = os.path.dirname(os.path.abspath(__file__))
	print( 'we are',frozen,'frozen')
	print( 'bundle dir is', bundle_dir )
	print( 'sys.argv[0] is', sys.argv[0] )
	print( 'sys.executable is', sys.executable )
	print( 'os.getcwd is', os.getcwd() )



LD_LIBRARY_PATH / LIBPATH considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This environment variable is used to discover libraries, it is the library
search path - on GNU/Linux and \*BSD `LD_LIBRARY_PATH` is used, on AIX it is
`LIBPATH`.

If it exists,
PyInstaller saves the original value to `*_ORIG`, then modifies the search
path so that the bundled libraries are found first by the bundled code.

But if your code executes a system program, you often do not want that this
system program loads your bundled libraries (that are maybe not compatible
with your system program) - it rather should load the correct libraries from
the system locations like it usually does.

Thus you need to restore the original path before creating the subprocess
with the system program.

::

    env = dict(os.environ)  # make a copy of the environment
    lp_key = 'LD_LIBRARY_PATH'  # for GNU/Linux and *BSD.
    lp_orig = env.get(lp_key + '_ORIG')
    if lp_orig is not None:
        env[lp_key] = lp_orig  # restore the original, unmodified value
    else:
        # This happens when LD_LIBRARY_PATH was not set.
        # Remove the env var as a last resort:
        env.pop(lp_key, None)
    p = Popen(system_cmd, ..., env=env)  # create the process


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
