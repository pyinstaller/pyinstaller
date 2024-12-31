How to Install PyInstaller
===============================

PyInstaller is available as a regular Python package.
The source archives for released versions are available from PyPI_,
but it is easier to install the latest version using pip_::

    pip install pyinstaller

.. note::

    PyInstaller is split into two packages ``pyinstaller`` and
    ``pyinstaller-hooks-contrib``. These should be kept approximately (roughly
    within a year of each other) in sync. To that end, if you choose to pin your
    ``pyinstaller`` version, please also pin ``pyinstaller-hooks-contrib``. If
    you upgrade ``pyinstaller``, you will also need to upgrade
    ``pyinstaller-hooks-contrib``.

To upgrade existing PyInstaller installation to the latest version, use::

    pip install --upgrade pyinstaller

To install the current development version, use::

    pip install https://github.com/pyinstaller/pyinstaller/tarball/develop

To install directly using pip's built-in git checkout support, use::

    pip install git+https://github.com/pyinstaller/pyinstaller

or to install specific branch (e.g., ``develop``)::

    pip install git+https://github.com/pyinstaller/pyinstaller@develop

Installing from the source archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The source code archive for released versions of PyInstaller are
available at PyPI_ and on `PyInstaller Downloads`_ page.

.. Note::
    Even though the source archive provides the ``setup.py`` script,
    installation via ``python setup.py install`` has been deprecated
    and should not be used anymore. Instead, run ``pip install .`` from
    the unpacked source directory, as described below.

The installation procedure is:
    1. Unpack the source archive.

    2. Move into the unpacked source directory.

    3. Run ``pip install .`` from the unpacked source directory. If
       installing into system-wide python installation, administrator
       privilege is required.

The same procedure applies to installing from manual git checkout::

    git clone https://github.com/pyinstaller/pyinstaller
    cd pyinstaller
    pip install .

If you intend to make changes to the source code and want them to take
effect immediately, without re-installing the package each time, you
can install it in editable mode::

    pip install -e .

For platforms other than Windows, GNU/Linux and macOS, you must first
build the bootloader for your platform: see :ref:`Building the Bootloader`.
After the bootloader has been built, use the ``pip install .`` command
to complete the installation.


.. _`pyinstaller_not_in_path`:

Troubleshooting missing PyInstaller command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In a properly setup Python environment, the command ``pyinstaller`` should now
exist on the execution path and the command below should display PyInstaller's
version. ::

    pyinstaller --version

If the command is not found, make sure that the ``PATH`` (the executable search
path) environment variable includes the directory that the ``pyinstaller``
executable was installed into.

* On Windows, this location is either of the paths returned by::

    import sysconfig; print(sysconfig.get_path("scripts"))
    import site; print(site.USER_BASE + "\\Scripts")

* On UNIX, this location is either of the paths returned by::

    import sysconfig; print(sysconfig.get_path("scripts"))
    import site; print(site.USER_BASE + "/bin")

To display the current path in Windows the command is ``echo %PATH%`` and on
other systems, ``echo $PATH``.

.. Note::
    If you cannot use the ``pyinstaller`` command due to the scripts
    directory not being in ``PATH``, you can instead invoke the
    ``PyInstaller`` module, by running ``python -m PyInstaller``
    (pay attention to the module name, which is case sensitive).
    This form of invocation is also useful when you have PyInstaller
    installed in multiple python environments, and you cannot be sure
    from which installation the ``pyinstaller`` command will be ran.


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

* ``pyi-set_version`` can be used to apply previously-extracted version
  resource to an existing Windows executable.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
