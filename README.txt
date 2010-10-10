_PyInstaller_
=============

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

 Non-Windows (32bit), Non-Linux (32/64bit) and Non-Mac OS X (32bit)
 users should first build the bootloader:
    cd source
    python ./waf configure build install


Major changes in this release
=============================
 See doc/CHANGES.txt
