_PyInstaller_
=============

Requirements
============
 Python:
    2.2+ (Python 3 not supported)
 OS:
    Windows (32bit/64bit)
    Linux (32bit/64bit)
    Mac OS X (32bit)

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

 For Windows (32/64bit), Linux (32/64bit) and Mac OS X (32bit) are
 available precompiled bootloaders.

 Other users should first try to build the bootloader:
    cd source
    python ./waf configure build install


Major changes in this release
=============================
 See doc/CHANGES.txt
