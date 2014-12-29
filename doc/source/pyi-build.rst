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
--distpath=DIR        Where to put the bundled app (default:
                      /home/hartmut/projekte/software/pyinstaller/dist)
--workpath=WORKPATH   Where to put all the temporary work files, .log, .pyz
                      and etc. (default:
                      /home/hartmut/projekte/software/pyinstaller/build)
-y, --noconfirm       Replace output directory (default:
                      SPECPATH/dist/SPECNAME) without asking for
                      confirmation
--upx-dir=UPX_DIR     Path to UPX utility (default: search the execution
                      path)
-a, --ascii           Do not include unicode encoding support (default:
                      included if available)
--clean               Clean PyInstaller cache and remove temporary files
                      before building.
--log-level=LOGLEVEL  Amount of detail in build-time console messages
                      (default: INFO, choose one of DEBUG, INFO, WARN,
                      ERROR, CRITICAL)


SEE ALSO
=============

``pyi-makespec``\(1), The PyInstaller Manual, ``pyinstaller``\(1)

Project Homepage |Homepage|

.. include:: _definitions.txt
