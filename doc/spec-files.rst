.. _using spec files:

Using Spec Files
=================

When you execute

    ``pyinstaller`` *options*.. ``myscript.py``

the first thing |PyInstaller| does is to build a spec (specification) file
``myscript.spec``.
That file is stored in the ``--specpath=`` directory,
by default the current directory.

The spec file tells |PyInstaller| how to process your script.
It encodes the script names and most of the options
you give to the ``pyinstaller`` command.
The spec file is actually executable Python code.
|PyInstaller| builds the app by executing the contents of the spec file.

For many uses of |PyInstaller| you do not need to examine or modify the spec file.
It is usually enough to
give all the needed information (such as hidden imports)
as options to the ``pyinstaller`` command and let it run.

There are four cases where it is useful to modify the spec file:

* When you want to bundle data files with the app.
* When you want to include run-time libraries (``.dll`` or ``.so`` files) that
  |PyInstaller| does not know about from any other source.
* When you want to add Python run-time options to the executable.
* When you want to create a multiprogram bundle with merged common modules.

These uses are covered in topics below.

You create a spec file using this command:

    ``pyi-makespec`` *options* *name*\ ``.py`` [*other scripts* ...]

The *options* are the same options documented above
for the ``pyinstaller`` command.
This command creates the *name*\ ``.spec`` file but does not
go on to build the executable.

After you have created a spec file and modified it as necessary,
you build the application by passing the spec file to the ``pyinstaller`` command:

    ``pyinstaller`` *options* *name*\ ``.spec``

When you create a spec file, most command options are encoded in the spec file.
When you build from a spec file, those options cannot be changed.
If they are given on the command line they are ignored and
replaced by the options in the spec file.

Only the following command-line options have an effect when building from a spec file:

*  --upx-dir=
*  --distpath=
*  --workpath=
*  --noconfirm
*  --ascii


Spec File Operation
~~~~~~~~~~~~~~~~~~~~

After |PyInstaller| creates a spec file,
or opens a spec file when one is given instead of a script,
the ``pyinstaller`` command executes the spec file as code.
Your bundled application is created by the execution of the spec file.
The following is an shortened example of a spec file for a minimal, one-folder app::

	block_cipher = None
	a = Analysis(['minimal.py'],
             pathex=['/Developer/PItests/minimal'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
	pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
	exe = EXE(pyz,... )
	coll = COLLECT(...)

The statements in a spec file create instances of four classes,
``Analysis``, ``PYZ``, ``EXE`` and ``COLLECT``.

* A new instance of class ``Analysis`` takes a list of script names as input.
  It analyzes all imports and other dependencies.
  The resulting object (assigned to ``a``) contains lists of dependencies
  in class members named:

  - ``scripts``: the python scripts named on the command line;
  - ``pure``: pure python modules needed by the scripts;
  - ``binaries``: non-python modules needed by the scripts;
  - ``datas``: non-binary files included in the app.

* An instance of class ``PYZ`` is a ``.pyz`` archive (described
  under :ref:`Inspecting Archives` below), which contains all the
  Python modules from ``a.pure``.

* An instance of ``EXE`` is built from the analyzed scripts and the ``PYZ``
  archive. This object creates the executable file.

* An instance of ``COLLECT`` creates the output folder from all the other parts.

In one-file mode, there is no call to ``COLLECT``, and the
``EXE`` instance receives all of the scripts, modules and binaries.

You modify the spec file to pass additional values to ``Analysis`` and
to ``EXE``.


.. _adding files to the bundle:

Adding Files to the Bundle
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add files to the bundle, you create a list that describes the files
and supply it to the ``Analysis`` call.
To find the data files at run-time, see :ref:`Run-time Information`.


.. _adding data files:

Adding Data Files
------------------

To have data files included in the bundle, provide a list that
describes the files as the value of the ``datas=`` argument to ``Analysis``.
The list of data files is a list of tuples.
Each tuple has two values, both of which must be strings:

    * The first string specifies the file or files as they are in this system now.

    * The second specifies the name of the folder to contain
      the files at run-time.

For example, to add a single README file to the top level of a one-folder app,
you could modify the spec file as follows::

	a = Analysis(...
             datas=[ ('src/README.txt', '.') ],
             ...
             )

You have made the ``datas=`` argument a one-item list.
The item is a tuple in which the first string says the existing file
is ``src/README.txt``.
That file will be looked up (relative to the location of the spec file)
and copied into the top level of the bundled app.

The strings may use either ``/`` or ``\`` as the path separator character.
You can specify input files using "glob" abbreviations.
For example to include all the ``.mp3`` files from a certain folder::

	a = Analysis(...
             datas= [ ('/mygame/sfx/*.mp3', 'sfx' ) ],
             ...
             )

All the ``.mp3`` files in the folder ``/mygame/sfx`` will be copied
into a folder named ``sfx`` in the bundled app.

The spec file is more readable if you create the list of added files
in a separate statement::

    added_files = [
             ( '/mygame/sfx/*.mp3', 'sfx' ),
             ( 'src/README.txt', '.' )
             ]
	a = Analysis(...
             datas = added_files,
             ...
             )

You can also include the entire contents of a folder::

    added_files = [
             ( '/mygame/data', 'data' ),
             ( '/mygame/sfx/*.mp3', 'sfx' ),
             ( 'src/README.txt', '.' )
             ]

The folder ``/mygame/data`` will be reproduced under the name
``data`` in the bundle.


.. _using data files from a module:

Using Data Files from a Module
--------------------------------

If the data files you are adding are contained within a Python module,
you can retrieve them using ``pkgutils.get_data()``.

For example, suppose that part of your application is a module named ``helpmod``.
In the same folder as your script and its spec file you have this folder
arrangement::

	helpmod
		__init__.py
		helpmod.py
		help_data.txt

Because your script includes the statement ``import helpmod``, 
|PyInstaller| will create this folder arrangement in your bundled app.
However, it will only include the ``.py`` files.
The data file ``help_data.txt`` will not be automatically included.
To cause it to be included also, you would add a ``datas`` tuple
to the spec file::

	a = Analysis(...
             datas= [ ('helpmod/help_data.txt', 'helpmod' ) ],
             ...
             )

When your script executes, you could find ``help_data.txt`` by
using its base folder path, as described in the previous section.
However, this data file is part of a module, so you can also retrieve
its contents using the standard library function ``pkgutil.get_data()``::

	import pkgutil
	help_bin = pkgutil.get_data( 'helpmod', 'help_data.txt' )

In Python 3, this returns the contents of the ``help_data.txt`` file as a binary string.
If it is actually characters, you must decode it::

	help_utf = help_bin.decode('UTF-8', 'ignore')


.. _adding binary files:

Adding Binary Files
--------------------

To add binary files, make a list of tuples that describe the files needed.
Assign the list of tuples to the ``binaries=`` argument of Analysis.

Normally |PyInstaller| learns about ``.so`` and ``.dll`` libraries by
analyzing the imported modules.
Sometimes it is not clear that a module is imported;
in that case you use a ``--hidden-import=`` command option.
But even that might not find all dependencies.

Suppose you have a module ``special_ops.so`` that is written in C
and uses the Python C-API.
Your program imports ``special_ops``, and |PyInstaller| finds and
includes ``special_ops.so``.
But perhaps ``special_ops.so`` links to ``libiodbc.2.dylib``.
|PyInstaller| does not find this dependency.
You could add it to the bundle this way::

    a = Analysis(...
             binaries=[ ( '/usr/lib/libiodbc.2.dylib', 'libiodbc.dylib' ) ],
             ...

As with data files, if you have multiple binary files to add,
create the list in a separate statement and pass the list by name.

Advanced Methods of Adding Files
---------------------------------

|PyInstaller| supports a more advanced (and complex) way of adding
files to the bundle that may be useful for special cases.
See :ref:`The TOC and Tree Classes` below.


.. _giving run-time python options:

Giving Run-time Python Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass command-line options to the Python interpreter.
The interpreter takes a number of command-line options but only the
following are supported for a bundled app:

* ``v`` to write a message to stdout each time a module is initialized.

* ``u`` for unbuffered stdio.

* ``W`` and an option to change warning behavior: ``W ignore`` or
  ``W once`` or ``W error``.

To pass one or more of these options, 
create a list of tuples, one for each option, and pass the list as
an additional argument to the EXE call.
Each tuple has three elements:

* The option as a string, for example ``v`` or ``W ignore``.

* None

* The string ``OPTION``

For example modify the spec file this way::

    options = [ ('v', None, 'OPTION'), ('W ignore', None, 'OPTION') ]
    a = Analysis( ...
                )
    ...
    exe = EXE(pyz,
          a.scripts,
          options,   <--- added line
          exclude_binaries=...
          )


.. _spec file options for a mac os x bundle:

Spec File Options for a Mac OS X Bundle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you build a windowed Mac OS X app
(that is, running in Mac OS X, you specify the ``--onefile --windowed`` options),
the spec file contains an additional statement to
create the Mac OS X application bundle, or app folder::

    app = BUNDLE(exe,
             name='myscript.app',
             icon=None,
             bundle_identifier=None)

The ``icon=`` argument to ``BUNDLE`` will have the path to an icon file
that you specify using the ``--icon=`` option.
The ``bundle_identifier`` will have the value you specify with the
``--osx-bundle-identifier=`` option.

An ``Info.plist`` file is an important part of a Mac OS X app bundle.
(See the `Apple bundle overview`_ for a discussion of the contents
of ``Info.plist``.)

|PyInstaller| creates a minimal ``Info.plist``.
You can add or overwrite entries in the plist by passing an
``info_plist=`` parameter to the BUNDLE call.
The value of this argument is a Python dict.
Each key and value in the dict becomes a key and value in the ``Info.plist`` file.
For example, when you use PyQt5,
you can set ``NSHighResolutionCapable`` to ``True`` to let your app
also work in retina screen::

    app = BUNDLE(exe,
             name='myscript.app',
             icon=None,
             bundle_identifier=None
             info_plist={
             	'NSHighResolutionCapable': 'True'
             	},
             )

The ``info_plist=`` parameter only handles simple key:value pairs.
It cannot handle nested XML arrays.
For example, if you want to modify ``Info.plist`` to tell Mac OS X
what filetypes your app supports, you must add a 
``CFBundleDocumentTypes`` entry to ``Info.plist``
(see `Apple document types`_).
The value of that keyword is a list of dicts,
each containing up to five key:value pairs.

To add such a value to your app's ``Info.plist`` you must edit the
plist file separately after |PyInstaller| has created the app.
However, when you re-run |PyInstaller|, your changes will be wiped out.
One solution is to prepare a complete ``Info.plist`` file and
copy it into the app after creating it.

Begin by building and testing the windowed app.
When it works, copy the ``Info.plist`` prepared by |PyInstaller|.
This includes the ``CFBundleExecutable`` value as well as the
icon path and bundle identifier if you supplied them.
Edit the ``Info.plist`` as necessary to add more items
and save it separately.

From that point on, to rebuild the app call |PyInstaller| in a shell script,
and follow it with a statement such as::

    cp -f Info.plist dist/myscript.app/Contents/Info.plist

Multipackage Bundles
~~~~~~~~~~~~~~~~~~~~~

.. Note::
	This feature is broken in the |PyInstaller| 3.0 release.
	Do not attempt building multipackage bundles until the feature
	is fixed. If this feature is important to you,
	follow  and comment on `PyInstaller Issue #1527`_.

Some products are made of several different apps,
each of which might
depend on a common set of third-party libraries, or share code in other ways.
When packaging such an product it
would be a pity to treat each app in isolation, bundling it with
all its dependencies, because that means storing duplicate copies
of code and libraries.

You can use the multipackage feature to bundle a set of executable apps
so that they share single copies of libraries.
You can do this with either one-file or one-folder apps.
Each dependency (a DLL, for example) is packaged only once, in one of the apps.
Any other apps in the set that depend on that DLL
have an "external reference" to it, telling them
to extract that dependency from the executable file of the app that contains it.

This saves disk space because each dependency is stored only once.
However, to follow an external reference takes extra time when an app is starting up.
All but one of the apps in the set will have slightly slower launch times.

The external references between binaries include hard-coded
paths to the output directory, and cannot be rearranged.
If you use one-folder mode, you must
install all the application folders within a single parent directory.
If you use one-file mode, you must place all
the related applications in the same directory
when you install the application.

To build such a set of apps you must code a custom
spec file that contains  a call to the ``MERGE`` function.
This function takes a list of analyzed scripts,
finds their common dependencies, and modifies the analyses
to minimize the storage cost.

The order of the analysis objects in the argument list matters.
The MERGE function packages each dependency into the
first script from left to right that needs that dependency.
A script that comes later in the list and needs the same file
will have an external reference to the prior script in the list.
You might sequence the scripts to place the most-used scripts first in the list.

A custom spec file for a multipackage bundle contains one call to the MERGE function::

      MERGE(*args)

MERGE is used after the analysis phase and before ``EXE`` and ``COLLECT``.
Its variable-length list of arguments consists of
a list of tuples, each tuple having three elements:

* The first element is an Analysis object, an instance of class Analysis,
  as applied to one of the apps.
  
* The second element is the script name of the analyzed app (without the ``.py`` extension).

* The third element is the name for the executable (usually the same as the script).

MERGE examines the Analysis objects to learn the dependencies of each script.
It modifies these objects to avoid duplication of libraries and modules.
As a result the packages generated will be connected.


Example MERGE spec file
------------------------

One way to construct a spec file for a multipackage bundle is to
first build a spec file for each app in the package.
Suppose you have a product that comprises three apps named
(because we have no imagination) ``foo``, ``bar`` and ``zap``:

    ``pyi-makespec`` *options as appropriate...* ``foo.py``
    
    ``pyi-makespec`` *options as appropriate...* ``bar.py``
    
    ``pyi-makespec`` *options as appropriate...* ``zap.py``

Check for warnings and test each of the apps individually.
Deal with any hidden imports and other problems.
When all three work correctly,
combine the statements from the three files ``foo.spec``, ``bar.spec`` and ``zap.spec``
as follows.

First copy the Analysis statements from each,
changing them to give each Analysis object a unique name::

    foo_a = Analysis(['foo.py'],
            pathex=['/the/path/to/foo'],
            hiddenimports=[],
            hookspath=None)

    bar_a = Analysis(['bar.py'], etc., etc...

    zap_a = Analysis(['zap.py'], etc., etc...

Now call the MERGE method to process the three Analysis objects::

    MERGE( (foo_a, 'foo', 'foo'), (bar_a, 'bar', 'bar'), (zap_a, 'zap', 'zap') )

The Analysis objects ``foo_a``, ``bar_a``, and ``zap_a`` are modified
so that the latter two refer to the first for common dependencies.

Following this you can copy the ``PYZ``, ``EXE`` and ``COLLECT`` statements from
the original three spec files,
substituting the unique names of the Analysis objects
where the original spec files have ``a.``, for example::

    foo_pyz = PYZ(foo_a.pure)
    foo_exe = EXE(foo_pyz, foo_a.scripts, ... etc.
    foo_coll = COLLECT( foo_exe, foo_a.binaries, foo_a.datas... etc.

    bar_pyz = PYZ(bar_a.pure)
    bar_exe = EXE(bar_pyz, bar_a.scripts, ... etc.
    bar_coll = COLLECT( bar_exe, bar_a.binaries, bar_a.datas... etc.

(If you are building one-file apps, there is no ``COLLECT`` step.)
Save the combined spec file as ``foobarzap.spec`` and then build it::

    pyi-build foobarzap.spec

The output in the ``dist`` folder will be all three apps, but
the apps ``dist/bar/bar`` and ``dist/zap/zap`` will refer to
the contents of ``dist/foo/`` for shared dependencies.

There are several multipackage examples in the 
|PyInstaller| distribution folder under ``/tests/old_suite/multipackage``.

Remember that a spec file is executable Python.
You can use all the Python facilities (``for`` and ``with``
and the members of ``sys`` and ``io``)
in creating the Analysis
objects and performing the ``PYZ``, ``EXE`` and ``COLLECT`` statements.
You may also need to know and use :ref:`The TOC and Tree Classes` described below.

Globals Available to the Spec File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While a spec file is executing it has access to a limited set of global names.
These names include the classes defined by |PyInstaller|:
``Analysis``, ``BUNDLE``, ``COLLECT``, ``EXE``, ``MERGE``,
``PYZ``, ``TOC`` and ``Tree``,
which are discussed in the preceding sections.

Other globals contain information about the build environment:

``DISTPATH``
	The relative path to the ``dist`` folder where
	the application will be stored.
	The default path is relative to the current directory.
	If the ``--distpath=`` option is used, ``DISTPATH`` contains that value.

``HOMEPATH``
	The absolute path to the |PyInstaller|
	distribution, typically in the current Python site-packages folder.

``SPEC``
	The complete spec file argument given to the
	``pyinstaller`` command, for example ``myscript.spec``
	or ``source/myscript.spec``.

``SPECPATH``
	The path prefix to the ``SPEC`` value as returned by ``os.split()``.

``specnm``
	The name of the spec file, for example ``myscript``.

``workpath``
	The path to the ``build`` directory. The default is relative to
	the current directory. If the ``workpath=`` option is used,
	``workpath`` contains that value.

``WARNFILE``
	The full path to the warnings file in the build directory,
	for example ``build/warnmyscript.txt``.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
