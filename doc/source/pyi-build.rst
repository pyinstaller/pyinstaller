.. -*- mode: rst ; ispell-local-dictionary: "american" -*-

==========================
pyi-build
==========================
-------------------------------------------------------------
Build for your |PyInstaller| project
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

``pyi-build`` <options> SPECFILE

DESCRIPTION
============

``pyi-build`` builds the project as defined in the specfile.

Like with setuptools, by default directories ``build`` and ``dist``
will be created. ``build`` is a private workspace for caching some
information The generated files will be placed within the ``dist``
subdirectory; that's where the files you are interested in will be
placed.

In most cases, this will be all you have to do. If not, see `When
things go wrong` in the manual and be sure to read the introduction to
`Spec Files`.



OPTIONS
========

-h, --help            show this help message and exit
--buildpath=BUILDPATH
                      Buildpath (default:
                      SPECPATH/build/pyi.TARGET_PLATFORM/SPECNAME)
-y, --noconfirm       Remove output directory (default: SPECPATH/dist)
                      without confirmation
--upx-dir=UPX_DIR     Directory containing UPX (default: search in path).
--log-level=LOGLEVEL  Log level for Build.py (default: INFO, choose one 
                      of DEBUG, INFO, WARN, ERROR, CRITICAL)


SEE ALSO
=============

``pyi-makespec``\(1), The PyInstaller Manual, ``pyinstaller``\(1)

Project Homepage |Homepage|

.. include:: _definitions.txt
