.. _run-time information:

Run-time Information
=====================

Your app should run in a bundle exactly as it does when run from source.
However, you may want to learn at run-time whether the app is running from
source or whether it is bundled ("frozen"). You can use the following code to
check "are we bundled?"::

    import sys
    if getattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
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
    path_to_dat = path.join(path.dirname(__file__), 'file.dat')

In the bundled main script itself the above might not work, as it is unclear
where it resides in the package hierarchy. So in when trying to find data files
relative to the main script, ``sys._MEIPASS`` can be used. The following will
get the path to a file ``other-file.dat`` next to the main script if not
bundled and in the bundle folder if it is bundled::

    from os import path
    import sys
    bundle_dir = getattr(sys, '_MEIPASS', path.abspath(path.dirname(__file__)))
    path_to_dat = path.join(bundle_dir, 'other-file.dat')


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

	#!/usr/bin/python3
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
