.. -*- mode: rst ; ispell-local-dictionary: "american" -*-

==========================
pyi-configure
==========================
-------------------------------------------------------------
Configuring your PyInstaller setup
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

``pyi-configure`` <options>

DESCRIPTION
============

This will configure PyInstaller usage based on the current system, and
save some information into ``config.dat`` that would otherwise be
recomputed every time.

It can be rerun at any time if your configuration changes. It must be
run at least once before trying to build anything.

|PyInstaller| is dependant to the version of python you configure it
for. In other words, you will need a separate copy of |PyInstaller|
for each Python version you wish to work with *or* you'll need to
rerun ``pyi-configure`` every time you switch the Python version).


OPTIONS
========


-h, --help            Show help message and exit
--help-media-names    List available media and disctance names and exit
--target-platform=TARGET_PLATFORM
                      Target platform, required for cross-bundling
                      (default: current platform).
--upx-dir=UPX_DIR     Directory containing UPX.
--executable=EXECUTABLE
                      Python executable to use. Required for cross-bundling.
-C CONFIGFILE, --configfile=CONFIGFILE
                      Name of generated configfile (default: |config.dat|)
--log-level=LOGLEVEL  Log level Configure.py (default: INFO, choose one 
                      of DEBUG, INFO, WARN, ERROR, CRITICAL)


SEE ALSO
=============

``pyi-build``\(1), The PyInstaller Manual, ``pyinstaller``\(1)

Project Homepage |Homepage|

.. include:: _definitions.txt
