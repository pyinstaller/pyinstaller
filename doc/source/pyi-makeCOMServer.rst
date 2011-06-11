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

--debug
    Use the verbose version of the executable.

--verbose
    Register the COM server(s) with the quiet flag off.

--ascii
    do not include encodings (this is passed through to Makespec).

--out <dir>
    Generate the driver script and spec file in dir.


SEE ALSO
=============

``pyi-makespec``\(1), The PyInstaller Manual, ``pyinstaller``\(1)

Project Homepage |Homepage|

.. include:: _definitions.txt
