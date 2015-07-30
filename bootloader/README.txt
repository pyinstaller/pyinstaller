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
