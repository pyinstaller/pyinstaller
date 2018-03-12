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
or if you want to modify the |bootloader| source,
you need to build the |bootloader|.
To do this,

* Download and install Python, which is required for running `:command:waf`,
* `git clone` or download the source (see the
  :ref:`Download section on the web-site <website:Downloads>`),
* ``cd`` into the folder where you cloned or unpacked the source to,
* ``cd bootloader``, and
* make the bootloader with: ``python ./waf all``,
* test the build by ref:`running (parts of) the test-suite
  <running-the-test-suite>`.

This will produce the |bootloader| executables for your current platform
(of course, for Windows these files will have the ``.exe`` extension):

* :file:`../PyInstaller/bootloader/{OS_ARCH}/run`,
* :file:`../PyInstaller/bootloader/{OS_ARCH}/run_d`,
* :file:`../PyInstaller/bootloader/{OS_ARCH}/runw` (OS X and Windows only), and
* :file:`../PyInstaller/bootloader/{OS_ARCH}/runw_d` (OS X and Windows only).

The bootloaders architecture defaults to the machine's one, but can be changed
using the ``--target-arch=`` option – given the appropriate compiler and
development files are installed. E.g. to build a 32-bit bootloader on a 64-bit
machine, run::

  python ./waf all --target-arch=32bit


If this reports an error, read the detailed notes that follow,
then ask for technical help.

Supported platforms are

* GNU/Linux (using gcc)
* Windows (using Visual C++ or MinGW's gcc)
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

    sudo apt-get install build-essential

* On Fedora, RedHat and derivates::

    sudo yum groupinstall "Development Tools"

* For other Distributions please consult the distributions documentation.

Now you can build the bootloader as shown above.

Alternatively you may want to use the `linux64` build-guest
provided by the Vagrantfile (see below).


Building Linux Standard Base (LSB) compliant binaries (optional)
-----------------------------------------------------------------

By default, the bootloaders on Linux are ”normal“, non-LSB binaries, which
should be fine for all GNU/Linux distributions.

If for some reason you want to build Linux Standard Base (LSB) compliant
binaries [#]_, you can do so by specifying ``--lsb`` on the waf command line,
as follows::

       python ./waf distclean all --lsb

LSB version 4.0 is required for successfully building of |bootloader|. Please
refer to ``python ./waf --help`` for further options related to LSB building.

.. [#] Linux Standard Base (LSB) is a set of open standards that should
       increase compatibility among Linux distributions. Unfortunately it is
       not widely adopted and both Debian and Ubuntu dropped support for LSB
       in autumn 2015. Thus |PyInstaller| bootloader are no longer provided
       as LSB binary.


Building for Mac OS X
========================

On Mac OS X please install Xcode_, Apple's suite of tools for developing
software for Mac OS X.
This will get you the `clang` compiler.
Any version suitable for your platform should be fine.
`Xcode` can be also installed from your Mac OS X Install DVD.

Now you can build the bootloader as shown above.

Alternatively you may want to use the `darwin64` build-guest
provided by the Vagrantfile (see below).


.. _cross-building for mac os x:

Cross-Building for Mac OS X
-----------------------------------

For cross-compiling for OS X you need the Clang/LLVM compiler, the
`cctools` (ld, lipo, …), and the OSX SDK. Clang/LLVM is a cross compiler by
default and is available on nearly every GNU/Linux distribution, so you just
need a proper port of the cctools and the OS X SDK.

This is easy to get and needs to be done only once and the result can be
transferred to you build-system. The build-system can then be a normal
(somewhat current) GNU/Linux system. [#]_

.. [#] Please keep in mind that to avoid problems, the system you are using
       for the preparation steps should have the same architecture (and
       possible the same GNU/Linux distribution version) as the build-system.

Preparation: Get SDK and Build-tools
.......................................

For preparing the SDK and building the cctools, we use the very helpful
scripts from the `OS X Cross <https://github.com/tpoechtrager/osxcross>`
toolchain. If you re interested in the details, and what other features OS X
Cross offers, please refer to it's homepage.

Side-note: For actually accessing the OS X disk image file (`.dmg`),
`darling-dmg <https://github.com/darlinghq/darling-dmg>`_ is used. It allows
mounting `.dmg` s under Linux via FUSE.

For saving you reading OSXCross' documentation we prepared a virtual box
description performing all required steps.
If you are interested in the precise commands, please refer to
``packages_osxcross_debianoid``, ``prepare_osxcross_debianiod``, and
``build_osxcross`` in the Vagrantfile.

Please proceed as follows:

1. Download `XCode 7.3.x
   <https://developer.apple.com/downloads/index.action?name=Xcode%207.3` and
   save it to :file:`bootloader/sdks/osx/`. You will need to register an
   `Apple ID`, for which you may use a disposable e-mail-address, to search
   and download the files.

   Please make sure that you are complying to the license of the respective
   package.

2. Use the Vagrantfile to automatically build the SDK and tools::

     vagrant up build-osxcross && vagrant halt build-osxcross

   This should create the file :file:`bootloader/sdks/osx/osxcross.tar.xz`,
   which will then be installed on the build-system.

   If for some reason this fails, try running ``vagrant provision
   build-osxcross``.

3. This virtual machine is no longer used, you may now want to discard it
   using ``vagrant destroy build-osxcross``.


Building the Bootloader
.......................................

Again, simply use the Vagrantfile to automatically build the OS X bootloaders::

     export TARGET=OSX  # make the Vagrantfile build for OS X
     vagrant up linux64 && vagrant halt linux

This should create the bootloaders in
* :file:`../PyInstaller/bootloader/Darwin-{*}/`.

   If for some reason this fails, try running ``vagrant provision
   linux64``.

3. This virtual machine is no longer used, you may now want to discard it
   using::

     vagrant destroy build-osxcross

4. If you are finished with the OS X bootloaders, unset `TARGET` again::

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

The pre-compiled |bootloader| coming with PyInstaller are
self-contained static executable that imposes no restrictions
on the version of Python being used.

When building the bootloader yourself, you have to carefully choose
between three options:

1. Using the Visual Studio C++ compiler.

   This allows creating self-contained static executables,
   which can be used for all versions of Python.
   This is why the bootloaders delivered with PyInstaller are build using
   Visual Studio C++ compiler.

   You can use any Visual Studio version that is convenient
   (as long as it's supported by the waf build-tool).


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
   on many Windows installations – but i not guaranteed to exist.

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
       choco install -y python vcbuildtools

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
|bootloader| run for example::

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


Vagrantfile Virtual Machines
================================

PyInstaller maintains a set of virtual machine description for testing and
(cross-) building. For managing these boxes, we use `vagrant
<https://www.vagrantup.com/>`_.

All guests [#]_ will automatically build the bootloader when running
`vagrant up GUEST` or
`vagrant provision GUEST`. They will build both 32- and 64-bit bootloaders.

.. [#] Except of guest `osxcross`, which will build the OS X SDK and cctools
       as described in section :ref:`cross-building for mac os x`.

All guests (except of `darwin64`), when building the bootloaders, are sharing
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

    GUI=1 TARGET=OSX vagrant up darwin64

or like this::

    export TARGET=OSX
    vagrant provision linux64


We currently provide this guests:

:linux64:  GNU/Linux (some recent version) used to build the GNU/Linux
           bootloaders.

           * If ``TARGET=OS`` is set, cross-builds the bootloaders for OS X
             (see :ref:`cross-building for mac os x`).

           * If ``TARGET=WINDOWS`` is set, cross-builds the bootloaders
             for Windows using mingw. Please have in mind that this imposes
             the restrictions mentioned above.

           * Otherwise (which is the default) bootloaders for GNU/Linux are
             build.

:darwin64:  Mac OS X 'Yosemite' – not actually used by the PyInstaller team,
            but provided for testing.

            This guest, when building the bootloaders, does *not* put the
            built executables onto the build-host. You need to fetch them
            using::

             vagrant plugin install vagrant-scp vagrant-reload # required only once
             vagrant scp -a darwin64:/vagrant/PyInstaller/bootloader/Darwin-* \
                            ../PyInstaller/bootloader/

            This is due the fact that this machine doesn't include the
            Virtualbox guest additions and thus doesn't support shared
            folders.

:windows10: Windows 10, used for building the Windows bootloaders
            using Visual  C++.

            * If ``MINGW=1`` is set, the bootloaders will be build using
              MinGW. Please be aware of the restrictions mentioned above.

            .. note:: The Windows box uses password authentication, so in
                      some cases you need to enter the password (which is
                      `Passw0rd!`).

:build-osxcross: GNU/Linux guest used to build the OS X SDK and `cctools` as
                 described in section :ref:`cross-building for mac os x`.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
