.. _run-time information:

Run-time Information
=====================

Your app should run in a bundle exactly as it does when run from source.
However, you may need to learn at run-time
whether the app is running from source, or is "frozen" (bundled).
For example, you might have
data files that are normally found based on a module's ``__file__`` attribute.
That will not work when the code is bundled.

The |PyInstaller| |bootloader| adds the name ``frozen`` to the ``sys`` module.
So the test for "are we bundled?" is::

	import sys
	if getattr( sys, 'frozen', False ) :
		# running in a bundle
	else :
		# running live

When your app is running, it may need to access data files in any of
three general locations:

* Files that were bundled with it (see :ref:`Adding Data Files`).

* Files the user has placed with the app bundle, say in the same folder.

* Files in the user's current working directory.

The program has access to several path variables for these uses.


Using ``__file__`` and ``sys._MEIPASS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When your program is not frozen, the standard Python
variable ``__file__`` is the full path to the script now executing.
When a bundled app starts up,
the |bootloader| sets the ``sys.frozen`` attribute
and stores the absolute path to the bundle folder in ``sys._MEIPASS``.
For a one-folder bundle, this is the path to that folder, 
wherever the user may have put it.
For a one-file bundle, this is the path to the ``_MEIxxxxxx`` temporary folder
created by the |bootloader| (see :ref:`How the One-File Program Works`).


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



.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
