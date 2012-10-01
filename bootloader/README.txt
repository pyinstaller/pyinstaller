Bootloader
==========
Bootloader bootstraps Python for the frozen application. It is written in C 
and the code is very platform specific. The bootloader has to be kept
standalone without any dependencies on 3rd party libraries.

Directory Structure
-------------------
* common
  Shared code for Unix/Windows.
* crypto
  Crypto support for bootloader. This code is unmaintained.
* linux
  Code specific to Linux/Unix/OS X.
* windows
  Code specific to Windows.
