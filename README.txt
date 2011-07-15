_PyInstaller_
=============

Requirements
============
 Python:
    2.2+ (Python 3 not yet supported)
 OS:
    Windows (32bit/64bit)
       - pywin32 (http://pywin32.sf.net/) for Python 2.6+
    Linux (32bit/64bit)
       - ldd
       - objdump
    Mac OS X (32bit)
       - otool (included in Xcode)

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
