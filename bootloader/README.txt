==========
Bootloader
==========

Bootloader bootstraps Python for the frozen application. It is written in C 
and the code is very platform specific. The bootloader has to be kept
standalone without any dependencies on 3rd party libraries.

Directory Structure
===============================

* src
  Bootloader source code common for all platforms.
* windows
  Code specific to Windows.
* zlib
  Library to unzip Python modules. This library is included in bootloader
  for Windows. On other platforms the bootloader uses zlib library from the
  system.
* images
  PyInstaller icons for Windows bootloaders and the .app bundle on Mac OS X.

Build instructions
===============================

See <http://pyinstaller.rtfd.io/en/latest/bootloader-building.html>.

In short::

  ./waf all

or::

  ./waf --no-lsb all


Building for other platforms
===============================

To easy rebuilding the bootloader for other platforms and other
word-sizes, you may use the enclosed ``Vagrantfile``. Example::

Target Linux
---------------

The box ``linux64`` builds both 32- and 64-bit bootloaders.

Example usage::

  rm -f ../PyInstaller/bootloader/Linux-*/*
  vagrant up linux64       # will also build the build loader

  vagrant scp linux64:/vagrant/PyInstaller/bootloader/Linux-* \
               ../PyInstaller/bootloader/

  vagrant halt linux64

  # verify the bootloader has been rebuild
  git status ../PyInstaller/bootloader/


Target Windows
---------------

Building cross from linux to windows currently doesn't work, since our
``wscript`` is not prepared for cross-building.

.. note:: The windows box will be removed soon and the Linux boxes
    will be enhanced for cross-building.

The Windows box will build both the 32- and the 64-bit version. It
requires two `Vagrant` plugins::

   vagrant plugin install vagrant-reload vagrant-scp

.. note:: The Windows box uses password authentication, so you need to
   enter the password. The box also uses `rsync`-type shared folders,
   which are not available prior to provisioning. This is why the
   first ``vagrant up`` will fail.

Tested with MinGW-w64 from this archive: <https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/6.2.0/threads-posix/sjlj/x86_64-6.2.0-release-posix-sjlj-rt_v5-rev1.7z>

Example usage::

  rm -f ../PyInstaller/bootloader/Windows-*/*
  vagrant up windows10         # this will fail, just continue
  vagrant provision windows10  # will also rebuild

  vagrant scp windows10:/vagrant/PyInstaller/bootloader/Windows-* \
               ../PyInstaller/bootloader/

  vagrant halt windows10
  # verify the bootloader has been rebuild
  git status ../PyInstaller/bootloader/



Target OS X
---------------

Some code for OS X prepared, but the box does not start correctly. If
you have experience with OS X please help improving it. We are also
interested in cross-building for OS X.

