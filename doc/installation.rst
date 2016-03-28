How to Install |PyInstaller|
===============================

|PyInstaller| is a normal Python package.
You can download the archive from PyPi_,
but it is easier to install using pip_ where is is available,
for example::

    pip install pyinstaller

or upgrade to a newer version::

    pip install --upgrade pyinstaller

Installing in Windows
~~~~~~~~~~~~~~~~~~~~~~~

For Windows, PyWin32_ or the more recent pypiwin32_, is a prerequisite.
The latter is installed automatically when you install |PyInstaller|
using pip_ or `easy_install`_.
If necessary, follow the pypiwin32_ link to install it manually.

It is particularly easy to use pip-Win_ to install |PyInstaller|
along with the correct version of PyWin32_.
pip-Win_ also provides virtualenv_, which makes it simple
to maintain multiple different Python interpreters and install packages
such as |PyInstaller| in each of them.
(For more on the uses of virtualenv, see :ref:`Supporting Multiple Platforms` below.)

When pip-Win is working, enter this command in its Command field
and click Run:

  ``venv -c -i  pyi-env-name``

This creates a new virtual environment rooted at ``C:\Python\pyi-env-name``
and makes it the current environment.
A new command shell
window opens in which you can run commands within this environment.
Enter the command

  ``pip install PyInstaller``

Once it is installed, to use |PyInstaller|,

* Start pip-Win
* In the Command field enter ``venv pyi-env-name``
* Click Run

Then you have a command shell window in which commands such as
`pyinstaller` execute in that Python environment.

Installing in Mac OS X
~~~~~~~~~~~~~~~~~~~~~~~~

|PyInstaller| works with the default Python 2.7 provided with current
Mac OS X installations.
However, if you plan to use a later version of Python,
or if you use any of the major packages such as
PyQt, Numpy, Matplotlib, Scipy, and the like, we strongly
recommend that you install these using either `MacPorts`_ or `Homebrew`_.

|PyInstaller| users report fewer problems when they use a package manager
than when they attempt to install major packages individually.

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

For platforms other than Windows, Linux and Mac OS, you must first
build a |bootloader| program for your platform: see :ref:`Building the Bootloader`.
After the |bootloader| has been created,
use ``python setup.py install`` with administrator privileges
to complete the installation.



Verifying the installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

On all platforms, the command ``pyinstaller`` should now exist on the
execution path. To verify this, enter the command

  ``pyinstaller --version``

The result should resemble ``3.n`` for a released version,
and ``3.n.dev0-xxxxxx`` for a development branch.

If the command is not found, make sure the execution path includes
the proper directory:

* Windows: ``C:\PythonXY\Scripts`` where *XY* stands for the
  major and minor Python version number,
  for example ``C:\Python34\Scripts`` for Python 3.4)
* Linux: ``/usr/bin/``
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
*pyinstaller-folder*\ ``/pyinstaller.py``.
The other commands are found in *pyinstaller-folder* ``/cliutils/``
with meaningful names (``makespec.py``, etc.)


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
