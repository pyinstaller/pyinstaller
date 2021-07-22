.. _using spec files:

Using Spec Files
=================

When you execute

    ``pyinstaller`` *options*.. ``myscript.py``

the first thing |PyInstaller| does is to build a spec (specification) file
:file:`myscript.spec`.
That file is stored in the :option:`--specpath` directory,
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

    ``pyi-makespec`` *options* :file:`{name}.py` [*other scripts* ...]

The *options* are the same options documented above
for the ``pyinstaller`` command.
This command creates the :file:`{name}.spec` file but does not
go on to build the executable.

After you have created a spec file and modified it as necessary,
you build the application by passing the spec file to the ``pyinstaller`` command:

    ``pyinstaller`` *options* :file:`{name}.spec`

When you create a spec file, most command options are encoded in the spec file.
When you build from a spec file, those options cannot be changed.
If they are given on the command line they are ignored and
replaced by the options in the spec file.

Only the following command-line options have an effect when building from a spec file:

* :option:`--upx-dir`
* :option:`--distpath`
* :option:`--workpath`
* :option:`--noconfirm`
* :option:`--ascii`
* :option:`--clean`

.. _spec-file operations:

Spec File Operation
~~~~~~~~~~~~~~~~~~~~

After |PyInstaller| creates a spec file,
or opens a spec file when one is given instead of a script,
the ``pyinstaller`` command executes the spec file as code.
Your bundled application is created by the execution of the spec file.
The following is a shortened example of a spec file for a minimal, one-folder app::

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
  - ``pathex``: a list of paths to search for imports (like using
    :envvar:`PYTHONPATH`), including paths given by the :option:`--paths`
    option.
  - ``binaries``: non-python modules needed by the scripts, including names 
    given by the :option:`--add-binary` option;
  - ``datas``: non-binary files included in the app, including names given 
    by the :option:`--add-data` option.

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
When you bundle to a single folder (see :ref:`Bundling to One Folder`),
the added data files are copied into the folder with the executable.
When you bundle to a single executable (see :ref:`Bundling to One File`),
copies of added files are compressed into the executable, and expanded to the
:file:`_MEI{xxxxxx}` temporary folder before execution.
This means that any changes a one-file executable makes to an added file
will be lost when the application ends.

In either case, to find the data files at run-time, see :ref:`Run-time Information`.


.. _adding data files:

Adding Data Files
------------------

You can add data files to the bundle by using the :option:`--add-data` command option, or by
adding them as a list to the spec file.

When using the spec file, provide a list that
describes the files as the value of the ``datas=`` argument to ``Analysis``.
The list of data files is a list of tuples.
Each tuple has two values, both of which must be strings:

    * The first string specifies the file or files as they are in this system now.

    * The second specifies the name of the *folder* to contain
      the files at run-time.

For example, to add a single README file to the top level of a one-folder app,
you could modify the spec file as follows::

	a = Analysis(...
             datas=[ ('src/README.txt', '.') ],
             ...
             )

And the command line equivalent (see
:ref:`What To Bundle, Where To Search`
for platform-specific details)::

	pyinstaller --add-data 'src/README.txt:.' myscript.py

You have made the ``datas=`` argument a one-item list.
The item is a tuple in which the first string says the existing file
is :file:`src/README.txt`.
That file will be looked up (relative to the location of the spec file)
and copied into the top level of the bundled app.

The strings may use either ``/`` or ``\`` as the path separator character.
You can specify input files using "glob" abbreviations.
For example to include all the ``.mp3`` files from a certain folder::

	a = Analysis(...
             datas= [ ('/mygame/sfx/*.mp3', 'sfx' ) ],
             ...
             )

All the ``.mp3`` files in the folder :file:`/mygame/sfx` will be copied
into a folder named ``sfx`` in the bundled app.

The spec file is more readable if you create the list of added files
in a separate statement::

    added_files = [
             ( 'src/README.txt', '.' ),
             ( '/mygame/sfx/*.mp3', 'sfx' )
             ]
	a = Analysis(...
             datas = added_files,
             ...
             )

You can also include the entire contents of a folder::

    added_files = [
             ( 'src/README.txt', '.' ),
             ( '/mygame/data', 'data' ),
             ( '/mygame/sfx/*.mp3', 'sfx' )
             ]

The folder :file:`/mygame/data` will be reproduced under the name
:file:`data` in the bundle.


.. _using data files from a module:

Using Data Files from a Module
--------------------------------

If the data files you are adding are contained within a Python module,
you can retrieve them using ``pkgutil.get_data()``.

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
The data file :file:`help_data.txt` will not be automatically included.
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

This returns the contents of the :file:`help_data.txt`
file as a binary string.
If it is actually characters, you must decode it::

	help_utf = help_bin.decode('UTF-8', 'ignore')


.. _adding binary files:

Adding Binary Files
--------------------

.. Note:: `Binary` files refers to DLLs, dynamic libraries, shared
   object-files, and such, which |PyInstaller| is going to search for further
   `binary` dependencies. Files like images and PDFs should go into the
   ``datas``.

You can add binary files to the bundle by using the :option:`--add-binary` command option,
or by adding them as a list to the spec file.
In the spec file, make a list of tuples that describe the files needed.
Assign the list of tuples to the ``binaries=`` argument of Analysis.
 
Adding binary files works in a similar way as adding data files. As described in 
:ref:`Adding Binary Files`, each tuple should have two values:

    * The first string specifies the file or files as they are in this system now.

    * The second specifies the name of the *folder* to contain
      the files at run-time.

Normally |PyInstaller| learns about ``.so`` and ``.dll`` libraries by
analyzing the imported modules.
Sometimes it is not clear that a module is imported;
in that case you use a :option:`--hidden-import` command option.
But even that might not find all dependencies.

Suppose you have a module ``special_ops.so`` that is written in C
and uses the Python C-API.
Your program imports ``special_ops``, and |PyInstaller| finds and
includes ``special_ops.so``.
But perhaps ``special_ops.so`` links to ``libiodbc.2.dylib``.
|PyInstaller| does not find this dependency.
You could add it to the bundle this way::

    a = Analysis(...
             binaries=[ ( '/usr/lib/libiodbc.2.dylib', '.' ) ],
             ...

Or via the command line (again, see
:ref:`What To Bundle, Where To Search`
for platform-specific details)::

	pyinstaller --add-binary '/usr/lib/libiodbc.2.dylib:.' myscript.py

If you wish to store ``libiodbc.2.dylib`` on a specific folder inside the bundle, 
for example ``vendor``, then you could specify it, using the second element of the tuple::

    a = Analysis(...
             binaries=[ ( '/usr/lib/libiodbc.2.dylib', 'vendor' ) ],
             ...

As with data files, if you have multiple binary files to add,
to improve readability,
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

.. Note:: The unbuffered stdio mode (the ``u`` option) enables unbuffered
   binary layer of ``stdout`` and ``stderr`` streams on all supported Python
   versions. The unbuffered text layer requires Python 3.7 or later.


.. _spec file options for a mac os x bundle:

Spec File Options for a Mac OS X Bundle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you build a windowed Mac OS X app
(that is, running in Mac OS X, you specify the :option:`--onefile`
:option:`--windowed` options),
the spec file contains an additional statement to
create the Mac OS X application bundle, or app folder::

    app = BUNDLE(exe,
             name='myscript.app',
             icon=None,
             bundle_identifier=None)

The ``icon=`` argument to ``BUNDLE`` will have the path to an icon file
that you specify using the :option:`--icon` option.
The ``bundle_identifier`` will have the value you specify with the
:option:`--osx-bundle-identifier` option.

An :file:`Info.plist` file is an important part of a Mac OS X app bundle.
(See the `Apple bundle overview`_ for a discussion of the contents
of ``Info.plist``.)

|PyInstaller| creates a minimal :file:`Info.plist`.
The ``version`` option can be used to set the application version
using the CFBundleShortVersionString Core Foundation Key.

You can add or overwrite entries in the plist by passing an
``info_plist=`` parameter to the BUNDLE call.  Its argument should be a
Python dict with keys and values to be included in the :file:`Info.plist`
file.
|PyInstaller| creates :file:`Info.plist` from the info_plist dict
using the Python Standard Library module plistlib_.
plistlib can handle nested Python objects (which are translated to nested
XML), and translates Python data types to the proper :file:`Info.plist`
XML types.  Here's an example::

    app = BUNDLE(exe,
             name='myscript.app',
             icon=None,
             bundle_identifier=None,
             version='0.0.1',
             info_plist={
             	'NSPrincipalClass': 'NSApplication',
                'NSAppleScriptEnabled': False,
                'CFBundleDocumentTypes': [
                    {
                        'CFBundleTypeName': 'My File Format',
                        'CFBundleTypeIconFile': 'MyFileIcon.icns',
                        'LSItemContentTypes': ['com.example.myformat'],
                        'LSHandlerRank': 'Owner'
                        }
                    ]
             	},
             )

In the above example, the key/value ``'NSPrincipalClass': 'NSApplication'`` is
necessary to allow Mac OS X to render applications using retina resolution.
The key ``'NSAppleScriptEnabled'`` is assigned the Python boolean
``False``, which will be output to :file:`Info.plist` properly as ``<false/>``.
Finally the key ``CFBundleDocumentTypes`` tells Mac OS X what filetypes your
application supports (see `Apple document types`_).


.. _posix specific options:

POSIX Specific Options
~~~~~~~~~~~~~~~~~~~~~~

By default all required system libraries are bundled.
To exclude all or most non-Python shared system libraries from the bundle,
you can add a call to the function ``exclude_system_libraries``
from the Analysis class.
System libraries are defined as files that come from under ``/lib*`` or
``/usr/lib*``
as is the case on POSIX and related operating systems.
The function accepts an optional parameter
that is a list of file wildcards exceptions,
to not exclude library files that match those wildcards in the bundle.
For example to exclude all non-Python system libraries except "libexpat"
and anything containing "krb" use this::

    a = Analysis(...)

    a.exclude_system_libraries(list_of_exceptions=['libexpat*', '*krb*'])


.. _splash screen target:


The :mod:`Splash` Target
~~~~~~~~~~~~~~~~~~~~~~~~~

For a splash screen to be displayed by the bootloader, the :mod:`Splash` target must be called
at build time. This class can be added when the spec file is created with the command-line
option :option:`--splash IMAGE_FILE <--splash>`. By default, the option to
display the optional text is disabled
(``text_pos=None``). For more information about the splash screen, see :ref:`splash screen`
section. The :mod:`Splash` Target looks like this::

   a = Analysis(...)

   splash = Splash('image.png',
                   binaries=a.binaries,
                   datas=a.datas,
                   text_pos=(10, 50),
                   text_size=12,
                   text_color='black')

Splash bundles the required resources for the splash screen into a file,
which will be included in the CArchive.

A :mod:`Splash` has two outputs, one is itself and one is stored in
``splash.binaries``. Both need to be passed on to other build targets in
order to enable the splash screen.
To use the splash screen in a **onefile** application, please follow this example::

   a = Analysis(...)

   splash = Splash(...)

   # onefile
   exe = EXE(pyz,
             a.scripts,
             splash,                   # <-- both, splash target
             splash.binaries,          # <-- and splash binaries
             ...)

In order to use the splash screen in a **onedir** application, only a small change needs
to be made. The ``splash.binaries`` attribute has to be moved into the ``COLLECT`` target,
since the splash binaries do not need to be included into the executable::

   a = Analysis(...)

   splash = Splash(...)

   # onedir
   exe = EXE(pyz,
             splash,                   # <-- splash target
             a.scripts,
             ...)
   coll = COLLECT(exe,
                  splash.binaries,     # <-- splash binaries
                  ...)

On Windows/macOS images with per-pixel transparency are supported. This allows
non-rectengular splash screen images. On Windows the transparent borders of the image
are hard-cuted, meaning that fading transparent values are not supported. There is
no common implementation for non-rectengular windows on Linux, so images with per-
pixel transparency is not supported.

The splash target can be configured in various ways. The constructor of the :mod:`Splash`
target is as follows:

.. automethod:: PyInstaller.building.splash.Splash.__init__


Multipackage Bundles
~~~~~~~~~~~~~~~~~~~~~

Some products are made of several different apps,
each of which might
depend on a common set of third-party libraries, or share code in other ways.
When packaging such a product it
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
combine the statements from the three files :file:`foo.spec`,
:file:`bar.spec` and :file:`zap.spec`
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

The output in the :file:`dist` folder will be all three apps, but
the apps :file:`dist/bar/bar` and :file:`dist/zap/zap` will refer to
the contents of :file:`dist/foo/` for shared dependencies.

There are several multipackage examples in the 
|PyInstaller| distribution folder under :file:`tests/functional/specs`.

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
``PYZ``, ``TOC``, ``Tree`` and ``Splash``,
which are discussed in the preceding sections.

Other globals contain information about the build environment:

``DISTPATH``
	The relative path to the :file:`dist` folder where
	the application will be stored.
	The default path is relative to the current directory.
	If the :option:`--distpath` option is used, ``DISTPATH`` contains that value.

``HOMEPATH``
	The absolute path to the |PyInstaller|
	distribution, typically in the current Python site-packages folder.

``SPEC``
	The complete spec file argument given to the
	``pyinstaller`` command, for example :file:`myscript.spec`
	or :file:`source/myscript.spec`.

``SPECPATH``
	The path prefix to the ``SPEC`` value as returned by ``os.path.split()``.

``specnm``
	The name of the spec file, for example :file:`myscript`.

``workpath``
	The path to the :file:`build` directory. The default is relative to
	the current directory. If the ``workpath=`` option is used,
	``workpath`` contains that value.

``WARNFILE``
	The full path to the warnings file in the build directory,
	for example :file:`build/warn-myscript.txt`.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
