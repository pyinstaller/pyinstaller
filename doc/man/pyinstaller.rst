==========================
pyinstaller
==========================

.. raw:: manpage

   .\" disable justification (adjust text to left margin only)
   .ad l
   \

SYNOPSIS
==========

``pyinstaller`` <options> SCRIPT

DESCRIPTION
============

Automatically calls pyi-configure, pyi-makespec and pyi-build in one
run. In most cases, running ``pyinstaller`` will be all you have to
do.

Please see the PyInstaller Manual for more information.


OPTIONS
========

.. include:: _pyinstaller-options.tmp

ENVIRONMENT VARIABLES
=====================

====================== ========================================================
PYINSTALLER_CONFIG_DIR This changes the directory where PyInstaller caches some
                       files. The default location for this is operating system
                       dependent, but is typically a subdirectory of the home
                       directory.
====================== ========================================================

SEE ALSO
=============

``pyi-configure``\(1), ``pyi-makespec``\(1), ``pyi-build``\(1), The
PyInstaller Manual, ``pyinstaller``\(1)

Project Homepage |Homepage|

.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
