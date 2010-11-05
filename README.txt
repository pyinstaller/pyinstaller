_PyInstaller 1.3_
=================

Use
===
 See doc/Manual.html

Installation in brief
=====================
 Non-Windows users should first build the bootloader:
    cd source/linux
    python ./Make.py
    make

 Everyone should:
    python Configure.py
    python Makespec.py /path/to/yourscript.py
    python Build.py /path/to/yourscript.spec
    .done.


Linux notes
===========
You will need some basic C/C++ compilation packages installed
on your computer to be able to build the bootloader. Debian/Ubuntu
users can run:

    sudo apt-get install build-essential python-dev zlib1g-dev



Major changes in this release
=============================
 See doc/CHANGES.txt
