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


Building for LINUX
~~~~~~~~~~~~~~~~~~~~~

By default, the bootloaders on Linux are LSB binaries.

LSB is a set of open standards that should increase compatibility among Linux
distributions.
|PyInstaller| produces a bootloader as an LSB binary in order
to increase compatibility for packaged applications among distributions.

*Note:* LSB version 4.0 is required for successfull building of |bootloader|.

On Debian- and Ubuntu-based distros, you can install LSB 4.0 tools by adding
the following repository to the sources.list file::

        deb http://ftp.linux-foundation.org/pub/lsb/repositories/debian lsb-4.0 main

then after having update the apt repository::

        sudo apt-get update

you can install LSB 4.0::

        sudo apt-get install lsb lsb-build-cc

Most other distributions contain only LSB 3.0 in their software
repositories and thus LSB build tools 4.0 must be downloaded by hand.
From Linux Foundation download `LSB sdk 4.0`_ for your architecture.

Unpack it by::

        tar -xvzf lsb-sdk-4.0.3-1.ia32.tar.gz

To install it run::

        cd lsb-sdk
        ./install.sh


After having installed the LSB tools, you can follow the standard building
instructions.

*NOTE:* if for some reason you want to avoid LSB compilation, you can
do so by specifying --no-lsb on the waf command line, as follows::

       python waf configure --no-lsb build install

This will also produce ``support/loader/YOUR_OS/run``,
``support/loader/YOUR_OS/run_d``, ``support/loader/YOUR_OS/runw`` and
``support/loader/YOUR_OS/runw_d``, but they will not be LSB binaries.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
