Bootloader
==========
Bootloader bootstraps Python for the frozen application. It is written in C 
and the code is very platform specific. The bootloader has to be kept
standalone without any dependencies on 3rd party libraries.

Directory Structure
-------------------
* common
  Shared code for Unix/Windows.
* linux
  Code specific to Linux/Unix/OS X.
* windows
  Code specific to Windows.
* zlib
  Library to unzip Python modules. This library is included in bootloader
  for Windows.
* images
  PyInstaller icons for Windows bootloaders and the .app bundle on Mac OS X.
