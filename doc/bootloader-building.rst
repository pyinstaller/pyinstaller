.. _building the bootloader:

=========================
Building the Bootloader
=========================

PyInstaller comes with pre-compiled bootloaders for some platforms in
the ``bootloader`` folder of the distribution folder.
When there is no pre-compiled bootloader for
the current platform (operating-system and word-size),
the pip_ setup will attempt to build one.

If there is no precompiled bootloader for your platform,
or if you want to modify the bootloader source,
you need to build the bootloader.
To do this,

* Download and install Python, which is required for running :command:`waf`,
* `git clone` or download the source from our `GitHub repository`_,
* ``cd`` into the folder where you cloned or unpacked the source to,
* ``cd bootloader``, and
* make the bootloader with: ``python ./waf all``,
* test the build by ref:`running (parts of) the test-suite
  <running-the-test-suite>`.

This will produce the bootloader executables for your current platform
(of course, for Windows these files will have the ``.exe`` extension):

* :file:`../PyInstaller/bootloader/{OS_ARCH}/run`,
* :file:`../PyInstaller/bootloader/{OS_ARCH}/run_d`,
* :file:`../PyInstaller/bootloader/{OS_ARCH}/runw` (macOS and Windows only), and
* :file:`../PyInstaller/bootloader/{OS_ARCH}/runw_d` (macOS and Windows only).

The bootloaders architecture defaults to the machine's one, but can be changed
using the :option:`--target-arch` option – given the appropriate compiler and
development files are installed. E.g. to build a 32-bit bootloader on a 64-bit
machine, run::

  python ./waf all --target-arch=32bit


If this reports an error, read the detailed notes that follow,
then ask for technical help.

By setting the environment variable ``PYINSTALLER_COMPILE_BOOTLOADER``
the pip_ setup will attempt to build the bootloader for your platform, even
if it is already present. Doing so would execute the command ``python ./waf configure all`` upon installation. You can also pass additional arguments to the build process by setting the ``PYINSTALLER_BOOTLOADER_WAF_ARGS`` environment variable.

Supported platforms are

* GNU/Linux (using gcc)
* Windows (using Visual C++ (VS2015 or later) or MinGW's gcc)
* Mac OX X (using clang)

Contributed platforms are

* AIX (using gcc or xlc)
* HP-UX  (using gcc or xlc)
* Solaris

For more information about cross-building please read on
and mind the section about the virtual machines
provided in the Vagrantfile.


Building for GNU/Linux
========================

Development Tools
----------------------

For building the bootloader you'll need a development environment.
You can run the following to install everything required:

* On Debian- or Ubuntu-like systems::

    sudo apt-get install build-essential zlib1g-dev

* On Fedora, RedHat and derivates::

    sudo yum groupinstall "Development Tools"
    sudo yum install zlib-devel

* For other Distributions please consult the distributions documentation.

Now you can build the bootloader as shown above.

Alternatively you may want to use the `linux64` build-guest
provided by the Vagrantfile (see below).


Building for macOS
========================

On macOS please install Xcode_, Apple's suite of tools for developing
software for macOS.
Instead of installing the full `Xcode` package, you can also install
and use `Command Line Tools for Xcode <https://developer.apple.com/download/more/>`_.
Installing either will provide the `clang` compiler.

If the toolchain supports `universal2` binaries, the 64-bit bootloaders
are by default built as `universal2` fat binaries that support both
`x86_64` and `arm64` architectures. This requires a recent version
of `Xcode` (12.2 or later). On older toolchains that lack support for
`universal2` binaries, a single-arch `x86_64` thin bootloader is
built. This behavior can be controlled by passing ``--universal2`` or
``--no-universal2``  flags to the ``waf`` build command. Attempting to
use ``--universal2`` flag and a toolchain that lacks support for
`universal2` binaries will result in configuration error.

The ``--no-universal2`` flag leaves the target architecture unspecified letting
the resultant executable's architecture be the C compiler's default (which is
almost certainly the architecture of the build machine). Should you want to
build a thin executable of either architecture, use the ``--no-universal2`` flag
and then optionally override the compiler, adding the ``-arch`` flag, via the
``CC`` environment variable.

Build a thin, native executable::

    python waf --no-universal2 all

Build a thin, ``x86_64`` executable (regardless of the build machine's
architecture)::

    CC='clang -arch x86_64' python waf --no-universal2  all

Build a thin, ``arm64`` executable (regardless of the build machine's
architecture)::

    CC='clang -arch arm64' python waf --no-universal2 all

By default, the build script targets macOS 10.13, which can be overridden by
exporting the MACOSX_DEPLOYMENT_TARGET environment variable.

.. _cross-building for macos:

Cross-Building for macOS
-----------------------------------

For cross-compiling for macOS you need the Clang/LLVM compiler, the
`cctools` (ld, lipo, …), and the macOS SDK. Clang/LLVM is a cross compiler by
default and is available on nearly every GNU/Linux distribution, so you just
need a proper port of the cctools and the macOS SDK.

This is easy to get and needs to be done only once and the result can be
transferred to you build-system. The build-system can then be a normal
(somewhat current) GNU/Linux system. [#]_

.. [#] Please keep in mind that to avoid problems, the system you are using
       for the preparation steps should have the same architecture (and
       possible the same GNU/Linux distribution version) as the build-system.

Preparation: Get SDK and Build-tools
.......................................

For preparing the SDK and building the cctools, we use the very helpful
scripts from the `OS X Cross <https://github.com/tpoechtrager/osxcross>`_
toolchain. If you are interested in the details, and what other features OS X
Cross offers, please refer to its homepage.

To save you reading the OSXCross' documentation, we prepared a virtual box
definition that performs all required steps.
If you are interested in the precise commands, please refer to
``packages_osxcross_debianoid``, ``prepare_osxcross_debianiod``, and
``build_osxcross`` in the Vagrantfile.

Please proceed as follows:

1. Download `Command Line Tools for Xcode <https://developer.apple.com/download/more/>`_
   12.2 or later. You will need an `Apple ID` to search and download the
   files; if you do not have one already, you can register it for free.

   Please make sure that you are complying to the license of the respective
   package.

2. Save the downloaded `.dmg` file to
   :file:`bootloader/_sdks/osx/Xcode_tools.dmg`.

3. Use the Vagrantfile to automatically build the SDK and tools::

     vagrant up build-osxcross && vagrant halt build-osxcross

   This should create the file :file:`bootloader/_sdks/osx/osxcross.tar.xz`,
   which will then be installed on the build-system.

   If for some reason this fails, try running ``vagrant provision
   build-osxcross``.

4. This virtual machine is no longer used, you may now want to discard it
   using ``vagrant destroy build-osxcross``.


Building the Bootloader
.......................................

Again, simply use the Vagrantfile to automatically build the macOS bootloaders::

     export TARGET=OSX  # make the Vagrantfile build for macOS
     vagrant up linux64 && vagrant halt linux64

This should create the bootloaders in
* :file:`../PyInstaller/bootloader/Darwin-{*}/`.

   If for some reason this fails, try running ``vagrant provision
   linux64``.

3. This virtual machine is no longer used, you may now want to discard it
   using::

     vagrant destroy build-osxcross

4. If you are finished with the macOS bootloaders, unset `TARGET` again::

     unset TARGET


If you don't want to use the build-guest provided by the Vagrant file,
perform the following steps
(see ``build_bootloader_target_osx`` in the Vagrantfile)::

    mkdir -p ~/osxcross
    tar -C ~/osxcross --xz -xf /vagrant/sdks/osx/osxcross.tar.xz
    PATH=~/osxcross/bin/:$PATH
    python ./waf all CC=x86_64-apple-darwin15-clang
    python ./waf all CC=i386-apple-darwin15-clang



Building for Windows
==========================

The pre-compiled bootloader coming with PyInstaller are
self-contained static executable that imposes no restrictions
on the version of Python being used.

When building the bootloader yourself, you have to carefully choose
between three options:

1. Using the Visual Studio C++ compiler.

   This allows creating self-contained static executables,
   which can be used for all versions of Python.
   This is why the bootloaders delivered with PyInstaller are build using
   Visual Studio C++ compiler.

   Visual Studio 2015 or later is required.


2. Using the `MinGW-w64`_ suite.

   This allows to create smaller, dynamically linked executables,
   but requires to use the same
   level of Visual Studio [#]_
   as was used to compile Python.
   So this bootloader will be tied to a specific version of Python.

   The reason for this is, that unlike Unix-like systems, Windows doesn’t
   supply a system standard C library,
   leaving this to the compiler.
   But Mingw-w64 doesn’t have a standard C library.
   Instead it links against msvcrt.dll, which happens to exist
   on many Windows installations – but is not guaranteed to exist.

.. [#] This description seems to be technically incorrect. I ought to depend
       on the C++ run-time library. If you know details, please open an
       issue_.


3. Using cygwin and MinGW.

   This will create executables for cygwin, not for 'plain' Windows.


In all cases you may want

* to set the path to include python, e.g. ``set PATH=%PATH%;c:\python35``,
* to peek into the Vagrantfile or
  :file:`../appveyor.yml` to learn how we are building.

You can also build the bootloaders for cygwin.


Build using Visual Studio C++
---------------------------------

* With our `wscript` file, you don't need to run ``vcvarsall.bat`` to ’switch’
  the environment between VC++ installations and target architecture. The
  actual version of C++ does not matter and the target architecture is
  selected by using the ``--target-arch=`` option.

* If you are not using Visual Studio for other work, installing only the
  standalone C++ build-tools might be the best option as it avoids bloating
  your system with stuff you don't need (and saves *a lot* if installation
  time).

  .. hint:: We recommend
     installing the build-tools software using the
     `chocolatey <https://chocolatey.org/>`_ package manager.
     While at a first glance it looks like overdose, this is the easiest
     way to install the C++ build-tools. It comes down to two lines in an
     administrative powershell::

       … one-line-install as written on the chocolatey homepage
       choco install -y python3 visualstudio2019-workload-vctools

* Useful Links:

  * `Microsoft Visual C++ Build-Tools 2015
    <http://landinghub.visualstudio.com/visual-cpp-build-tools>`_
  * `Microsoft Build-Tools for Visual Studio 2017.
    <https://www.visualstudio.com/downloads/#build-tools-for-visual-studio-2017>`_


After installing the C++ build-tool
you can build the bootloader as shown above.


Build using MinGW-w64
-----------------------

Please be aware of the restrictions mentioned above.

If Visual Studio is not convenient,
you can download and install the MinGW distribution from one of the
following locations:

* `MinGW-w64`_ required, uses gcc 4.4 and up.

* `TDM-GCC`_ - MinGW (not used) and MinGW-w64 installers

Note: Please mind that using cygwin's python or MinGW
when running ``./waf`` will
create executables for cygwin, not for Windows.

On Windows, when using MinGW-w64, add :file:`{PATH_TO_MINGW}\bin`
to your system ``PATH``. variable. Before building the
bootloader run for example::

        set PATH=C:\MinGW\bin;%PATH%

Now you can build the bootloader as shown above.
If you have installed both Visual C++ and MinGW,
you might need to add run ``python ./waf --gcc all``.



Build using cygwin and MinGW
--------------------------------

Please be aware that
this will create executables for cygwin, not for 'plain' Windows.

Use cygwin's ``setup.exe`` to install `python` and `mingw`.

Now you can build the bootloader as shown above.


Building for AIX
===================

* By default AIX builds 32-bit executables.
* For 64-bit executables set the environment variable :envvar:`OBJECT_MODE`.

When creating a 64-bit build, the compiler and other AIX utilities that
work with binary files (for example, the :command:`strip` utility) may
need to be passed the ``-X64`` flag to force 64-bit mode. Rather than
passing this flag to every command, the preferred way to provide this
setting is to use the :envvar:`OBJECT_MODE` environment variable.

Depending on whether you are using 32-bit or 64-bit Python build,
you may therefore need to set or unset the :envvar:`OBJECT_MODE` environment
variable prior to running  ``waf`` in order to build a matching type of the
bootloader executable.

To determine whether you are using 32-bit or 64-bit Python, use the following
command::

    python -c "import sys; print(sys.maxsize <= 2**32)"

If the output of above command is ``True``, your Python is 32-bit, and
you should build bootloader using the following commands::

    unset OBJECT_MODE
    python ./waf all

Otherwise (64-bit Python), you should use the following commands::

    export OBJECT_MODE=64
    python ./waf all

.. note:: While :envvar:`OBJECT_MODE` environment variable is honored by
   IBM's :command:`xlc_r` compiler, the :command:`gcc` compiler from *AIX
   Toolbox for Open Source Software* (found in :command:`/opt/freeware/bin/gcc`)
   does not seem to honor it. When using this compiler, you need to set
   the target architecture by passing ``--target-arch`` option to ``waf``,
   for example::

     python ./waf all --target-arch=64bit

To build the bootloader, you will need a compiler compatible (identical)
with the one that was used to build Python itself.

.. note:: Python compiled with a different version of gcc that you are using
   might not be compatible enough.
   GNU tools are not always binary compatible.

To identify the compiler that was used to build Python, you can use the
following command::

    python -c "import sysconfig; print(sysconfig.get_config_var('CC'))"

If the compiler is :command:`gcc` you may need additional RPMs installed
to support the GNU run-time dependencies.

When the IBM compiler is used, no additional prerequisites are expected.
The recommended value for :envvar:`CC` environment variable with the
IBM compiler is :command:`xlc_r`.


Building for FreeBSD
====================

A FreeBSD bootloader may be built with clang using :ref:`the usual steps
<building the bootloader>` on a FreeBSD machine.
Beware, however that any executable compiled natively on FreeBSD will only run
on equal or newer versions of FreeBSD.
In order to support older versions of FreeBSD, you must compile the oldest OS
version you wish to support.

Alternatively, the FreeBSD bootloaders may be cross compiled from Linux using
Docker and a `FreeBSD cross compiler image
<https://github.com/bwoodsend/freebsd-cross-build>`_.
This image is kept in sync with the oldest non end of life FreeBSD release so
that anything compiled on it will work on all active FreeBSD versions.

In a random directory:

* Start the docker daemon (usually with ``systemctl start docker`` - possibly
  requiring ``sudo`` if you haven't setup rootless docker).
* Download the latest cross compiler ``.tar.xz`` image from `here
  <https://github.com/bwoodsend/freebsd-cross-build/releases>`_.
* Import the image: ``docker image load -i freebsd-cross-build.tar.xz``.
  The cross compiler image is now saved under the name ``freebsd-cross-build``.
  You may discard the ``.tar.xz`` file if you wish.

Then from the root of this repository:

* Run:

  .. code-block:: bash

    docker run -v $(pwd):/io -it freebsd-cross-build bash -c "cd /io/bootloader; ./waf all"



Vagrantfile Virtual Machines
================================

PyInstaller maintains a set of virtual machine description for testing and
(cross-) building. For managing these boxes, we use `vagrant
<https://www.vagrantup.com/>`_.

All guests [#]_ will automatically build the bootloader when running
`vagrant up GUEST` or
`vagrant provision GUEST`. They will build both 32- and 64-bit bootloaders.

.. [#] Except of guest `osxcross`, which will build the macOS SDK and cctools
       as described in section :ref:`cross-building for macos`.

When building the bootloaders, the guests are sharing
the PyInstaller distribution folder and will put the built executables onto
the build-host (into :file:`../PyInstaller/bootloader/`).

Most boxes requires two `Vagrant` plugins to be installed::

   vagrant plugin install vagrant-reload vagrant-scp


Example usage::

  vagrant up linux64      # will also build the bootloader
  vagrant halt linux64    # or `destroy`

  # verify the bootloader has been rebuild
  git status ../PyInstaller/bootloader/


You can pass some parameters for configuring the Vagrantfile by setting
environment variables, like this::

    GUI=1 TARGET=OSX vagrant up linux64

or like this::

    export TARGET=OSX
    vagrant provision linux64


We currently provide this guests:

:linux64:  GNU/Linux (some recent version) used to build the GNU/Linux
           bootloaders.

           * If ``TARGET=OSX`` is set, cross-builds the bootloaders for macOS
             (see :ref:`cross-building for macos`).

           * If ``TARGET=WINDOWS`` is set, cross-builds the bootloaders
             for Windows using mingw. Please have in mind that this imposes
             the restrictions mentioned above.

           * Otherwise (which is the default) bootloaders for GNU/Linux are
             build.

:windows10: Windows 10, used for building the Windows bootloaders
            using Visual  C++.

            * If ``MINGW=1`` is set, the bootloaders will be build using
              MinGW. Please be aware of the restrictions mentioned above.

            .. note:: The Windows box uses password authentication, so in
                      some cases you need to enter the password (which is
                      `Passw0rd!`).

:build-osxcross: GNU/Linux guest used to build the macOS SDK and `cctools` as
                 described in section :ref:`cross-building for macos`.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
