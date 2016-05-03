Bootloader
==========
Bootloader bootstraps Python for the frozen application. It is written in C 
and the code is very platform specific. The bootloader has to be kept
standalone without any dependencies on 3rd party libraries.

Directory Structure
-------------------
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
----------------------

See <http://pythonhosted.org/PyInstaller/#building-the-bootloader>.

In short::

  ./waf all

or::

  ./waf --no-lsb all


Building for other platforms
-------------------------------

To easy rebuilding the bootloader for other platforms and other
word-sizes, you may use the enclosed ``Vagrantfile``. Example::

  rm -f ../PyInstaller/bootloader/Linux-32*/*
  vagrant up linux32 --provision # will also rebuild
  vagrant halt linux32
  # verify the bootloader has been rebuild
  git status ../PyInstaller/bootloader/

Currently only ``linux32`` and ``linux64`` are supported. But there is
some code for OS X prepared. If you have experience with OS X please
help improving it.
