==========================
pyinstaller
==========================

.. raw:: manpage

   .\" disable justification (adjust text to left margin only)
   .ad l
   \

SYNOPSIS
==========

``pyinstaller`` <options> SCRIPT...

``pyinstaller`` <options> SPECFILE


DESCRIPTION
============

PyInstaller is a program that freezes (packages) Python programs into
stand-alone executables, under Windows, Linux, Mac OS X, FreeBSD, Solaris and
AIX. Its main advantages over similar tools are that PyInstaller works with
Python 2.7 and 3.4—3.6, it builds smaller executables thanks to transparent
compression, it is fully multi-platform, and use the OS support to load the
dynamic libraries, thus ensuring full compatibility.

You may either pass one or more file-names of Python scripts or a single
`.spec`-file-name. In the first case, ``pyinstaller`` will generate a
`.spec`-file (as ``pyi-makespec`` would do) and immediately process it.

If you pass a `.spec`-file, this will be processed and most options given on
the command-line will have no effect.
Please see the PyInstaller Manual for more information.


OPTIONS
========

.. include:: _pyinstaller-options.tmp

ENVIRONMENT VARIABLES
=====================

:PYINSTALLER_CONFIG_DIR:
   This changes the directory where PyInstaller caches some files.
   The default location for this is operating system dependent,
   but is typically a subdirectory of the home directory.


SEE ALSO
=============

``pyi-makespec``\(1),
The PyInstaller Manual |Manual|,
Project Homepage |Homepage|


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
