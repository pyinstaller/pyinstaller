.. -*- mode: rst ; ispell-local-dictionary: "american" -*-

==========================
pyi-makeCOMServer
==========================
-------------------------------------------------------------
Windows COM Server support for |PyInstaller|
-------------------------------------------------------------
:Author:    Giovanni Bajo
:Copyright: 2005-2011 by Giovanni Bajo, based on previous work under copyright 2002 McMillan Enterprises, Inc.
:Version:   |PyInstallerVersion|
:Manual section: 1

.. raw:: manpage

   .\" disable justification (adjust text to left margin only)
   .ad l


SYNOPSIS
==========

``pyi-makeCOMServer`` <options> SCRIPT

DESCRIPTION
============

This will generate a new script ``drivescript.py`` and a spec file for
the script.

Please see the PyInstaller Manual for more information.


OPTIONS
========

.. include:: _pyi-make_comserver-options.tmp

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

``pyi-makespec``\(1), The PyInstaller Manual, ``pyinstaller``\(1)

Project Homepage |Homepage|

.. include:: _definitions.txt
