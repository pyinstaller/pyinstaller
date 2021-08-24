How to Install |PyInstaller|
===============================

|PyInstaller| is a normal Python package.
You can download the archive from PyPi_,
but it is easier to install using pip_ where is is available,
for example::

    pip install pyinstaller

or upgrade to a newer version::

    pip install --upgrade pyinstaller

To install the current development version use::

    pip install https://github.com/pyinstaller/pyinstaller/tarball/develop


Installing in Mac OS X
~~~~~~~~~~~~~~~~~~~~~~~~

Mac OS X 10.8 comes with Python 2.7 pre-installed by Apple.
However, Python 2.7 is end-of-life and no longer supported by |PyInstaller|,
also
major packages such as
PyQt, Numpy, Matplotlib, Scipy, and the like,
have dropped support for Python 2.7, too.
Thus we strongly
recommend that you install these using either `MacPorts`_ or `Homebrew`_.

|PyInstaller| users report fewer problems when they use a package manager
than when they attempt to install major packages individually.

Alternatively you might install Python 3 following the
`official guide <https://docs.python.org/3/using/mac.html>`_.


Installing from the archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If pip is not available, download the compressed archive from PyPI_.
If you are asked to test a problem using the latest development code,
download the compressed archive from the *develop* branch of
`PyInstaller Downloads`_ page.

Expand the archive.
Inside is a script named ``setup.py``.
Execute ``python setup.py install``
with administrator privilege to install or upgrade |PyInstaller|.

For platforms other than Windows, GNU/Linux and Mac OS, you must first
build a |bootloader| program for your platform: see :ref:`Building the Bootloader`.
After the |bootloader| has been created,
use ``python setup.py install`` with administrator privileges
to complete the installation.



Verifying the installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

On all platforms, the command ``pyinstaller`` should now exist on the
execution path. To verify this, enter the command::

    pyinstaller --version

The result should resemble ``3.n`` for a released version,
and ``3.n.dev0-xxxxxx`` for a development branch.

If the command is not found, make sure the execution path includes
the proper directory:

* Windows: ``C:\PythonXY\Scripts`` where *XY* stands for the
  major and minor Python version number,
  for example ``C:\Python34\Scripts`` for Python 3.4)
* GNU/Linux: ``/usr/bin/``
* OS X (using the default Apple-supplied Python) ``/usr/bin``
* OS X (using Python installed by homebrew) ``/usr/local/bin``
* OS X (using Python installed by macports) ``/opt/local/bin``

To display the current path in Windows the command is ``echo %path%``
and in other systems, ``echo $PATH``.


Installed commands
~~~~~~~~~~~~~~~~~~~~

The complete installation places these commands on the execution path:

* ``pyinstaller`` is the main command to build a bundled application.
  See :ref:`Using PyInstaller`.

* ``pyi-makespec`` is used to create a spec file. See :ref:`Using Spec Files`.

* ``pyi-archive_viewer`` is used to inspect a bundled application.
  See :ref:`Inspecting Archives`.

* ``pyi-bindepend`` is used to display dependencies of an executable.
  See :ref:`Inspecting Executables`.

* ``pyi-grab_version`` is used to extract a version resource from a Windows
  executable.  See :ref:`Capturing Windows Version Data`.

If you do not perform a complete installation
(installing via ``pip`` or executing ``setup.py``),
these commands will not be installed as commands.
However, you can still execute all the functions documented below
by running Python scripts found in the distribution folder.
The equivalent of the ``pyinstaller`` command is
:file:`{pyinstaller-folder}/pyinstaller.py`.
The other commands are found in :file:`{pyinstaller-folder}/cliutils/`
with meaningful names (``makespec.py``, etc.)


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
