.. _building the bootloader:

Building the Bootloader
=========================

PyInstaller comes with pre-compiled bootloaders for some platforms in
the ``bootloader`` folder of the distribution folder.
When there is no pre-compiled bootloader, the pip_ setup will attempt to build one.

If there is no precompiled bootloader for your platform,
or if you want to modify the |bootloader| source,
you need to build the |bootloader|.
To do this,

* ``cd`` into the distribution folder.
* ``cd bootloader``.
* Make the bootloader with: ``python ./waf distclean all``.

This will produce the |bootloader| executables,

* ``./PyInstaller/bootloader/YOUR_OS/run``,
* ``./PyInstaller/bootloader/YOUR_OS/run_d``
* ``./PyInstaller/bootloader/YOUR_OS/runw`` and
* ``./PyInstaller/bootloader/YOUR_OS/runw_d``

*Note:* If you have multiple versions of Python, the Python you use to run
``waf`` is the one whose configuration is used.

If this reports an error, read the detailed notes that follow,
then ask for technical help.


Development tools
~~~~~~~~~~~~~~~~~~~~

On Debian/Ubuntu systems, you can run the following to
install everything required::

    sudo apt-get install build-essential

On Fedora/RHEL and derivates, you can run the following::

    su
    yum groupinstall "Development Tools"

On Mac OS X you can get gcc by installing Xcode_. It is a suite of tools
for developing software for Mac OS X. It can be also installed from your
Mac OS X Install DVD. It is not necessary to install the version 4 of Xcode.

On Solaris and AIX the |bootloader| is built and tested with gcc.


Building for Windows
~~~~~~~~~~~~~~~~~~~~~~~~

On Windows you can use the Visual Studio C++ compiler
(Visual Studio 2008 is recommended).
A free version you can download is `Visual Studio Express`_.

*Note:* When compiling libs to link with Python it is important
to use the same level of Visual Studio as was used to compile Python.
*That is not the case here*. The |bootloader| is a self-contained static
executable that imposes no restrictions on the version of Python being used.
So you can use any Visual Studio version that is convenient.

If Visual Studio is not convenient,
you can download and install the MinGW distribution from one of the
following locations:

* `MinGW-w64`_ required, uses gcc 4.4 and up.

* `TDM-GCC`_ - MinGW (not used) and MinGW-w64 installers

On Windows, when using MinGW-w64, add ``PATH_TO_MINGW\bin``
to your system ``PATH``. variable. Before building the
|bootloader| run for example::

        set PATH=C:\MinGW\bin;%PATH%

Change to the ``bootloader`` subdirectory. Run::

        python ./waf distclean all

This will produce the bootloader executables ``run*.exe``
in the ``.\PyInstaller\bootloader\YOUR_OS`` directory.


Building Linux Standard Base (LSB) compliant binaries
============================================================

By default, the bootloaders on Linux are ”normal“, non-LSB binaries, which
should be fine for all GNU/Linux distributions.

If for some reason you want to build Linux Standard Base (LSB) compliant
binaries [*]_, you can do so by specifying ``--lsb`` on the waf command line,
as follows::

       python waf distclean all --lsb

LSB version 4.0 is required for successfull building of |bootloader|. Please
refer to ``python waf --help`` for further options related to LSB building.

The bootloaders will still end up in :file:`support/loader/{YOUR_OS}/run`.


.. [*] Linux Standard Base (LSB) is a set of open standards that should
       increase compatibility among Linux distributions. Unfortunalty it is
       not widely adopted and both Debian and Ubuntu dropped support for LSB
       in autumn 2015. Thus |PyInstaller| bootloader are no longer provided
       as LSB binary.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
