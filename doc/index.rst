==================
PyInstaller Manual
==================

:Version: |PyInstallerVersion|
:Homepage: |Homepage|
:Contact: pyinstaller@googlegroups.com
:Authors: David Cortesi, based on structure by Giovanni Bajo & William Caban, based on Gordon McMillan's manual
:Copyright: This document has been placed in the public domain.


|PyInstaller| bundles a Python application and all its dependencies into
a single package.
The user can run the packaged app without installing a Python interpreter or any modules.
|PyInstaller| supports Python 2.7 and Python 3.4+,
and correctly bundles the major Python packages
such as numpy, PyQt, Django, wxPython, and others.

|PyInstaller| is tested against Windows, Mac OS X, and Linux.
However, it is not a cross-compiler:
to make a Windows app you run |PyInstaller| in Windows;
to make a Linux app you run it in Linux, etc.
|PyInstaller| has been used successfully with AIX, Solaris, and FreeBSD,
but is not tested against them.


What's New This Release
~~~~~~~~~~~~~~~~~~~~~~~~

Release 3.0 is a major rewrite that adds Python 3 support,
better code quality through use of automated testing,
and resolutions for many old issues.

Functional changes include
removal of support for Python prior to 2.7,
an easier way to include data files
in the bundle (:ref:`Adding Files to the Bundle`),
and changes to the "hook" API (:ref:`Understanding PyInstaller Hooks`).

Contents:

.. toctree::
   :maxdepth: 2

   requirements
   license
   contributing
   installation
   operating-mode
   usage
   runtime-information
   spec-files
   feature-notes
   when-things-go-wrong
   advanced-topics
   hooks
   bootloader-building
   CHANGES
   CREDITS
   man-pages
   development/index


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
