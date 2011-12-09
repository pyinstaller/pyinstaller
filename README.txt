_PyInstaller_
=============

Requirements
============

Python:
    2.2+ (Python 3 not yet supported)

Windows (32bit/64bit):
  * Windows XP or newer.
  * pywin32 when using Python 2.6+
    http://sourceforge.net/projects/pywin32/

Linux (32bit/64bit)
  * ldd
    - Console application to print the shared libraries required 
      by each program or shared library.
  * objdump
    - Console application to display information from object files.

Mac OS X (32):
  * otool (included in Xcode)

Solaris (experimental)
  * ldd
  * objdump

AIX (experimental)
  * AIX 6.1 or newer.
    Python executables created using PyInstaller on AIX 6.1 should
    work on AIX 5.2/5.3. PyInstaller will not work with statically
    linked Python libraries which has been encountered in Python 2.2
    installations on AIX 5.x.
  * ldd
  * objdump


Use
===
 See doc/Manual.html

Installation in brief
=====================
 Everyone should:

    python Configure.py
    python Makespec.py /path/to/yourscript.py
    python Build.py /path/to/yourscript.spec
    .done.

 Alternative interface (default in development version)
 combining Configure.py/Makespec.py/Build.py:

    python pyinstaller.py /path/to/yourscript.py

    or

    python pyinstaller.py /path/to/yourscript.spec

 For Windows (32/64bit), Linux (32/64bit) and Mac OS X (32bit) are
 available precompiled bootloaders.

 Other users should first try to build the bootloader:

    cd source
    python ./waf configure build install


Major changes in this release
=============================
 See doc/CHANGES.txt
