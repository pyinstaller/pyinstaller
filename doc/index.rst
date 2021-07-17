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
|PyInstaller| supports Python 3.6 or newer,
and correctly bundles the major Python packages
such as numpy, PyQt, Django, wxPython, and others.

|PyInstaller| is tested against Windows, Mac OS X, and GNU/Linux.
However, it is not a cross-compiler:
to make a Windows app you run |PyInstaller| in Windows;
to make a GNU/Linux app you run it in GNU/Linux, etc.
|PyInstaller| has been used successfully with
AIX, Solaris, FreeBSD and OpenBSD
but testing against them is not part of our continuous integration tests.


What's New This Release
~~~~~~~~~~~~~~~~~~~~~~~~

Release 4.0 adds support for 3rd-party packages to provide PyInstaller hooks
along with the package. This allows Maintainers of other Python packages to
deliver up-to-date PyInstaller hooks as part of their package.
See our `sample project`__ for more information.

__ https://github.com/pyinstaller/hooksample

PyInstaller uses this option itself to provide updated hooks much faster:
Many hooks are moved into the new package `pyinstaller-hooks-contrib`__,
which is updated monthly.
This package is installed automatically when installing PyInstaller,
but can also be updated independently.

__ https://github.com/pyinstaller/pyinstaller-hooks-contrib

Finally, this version drops support for Python 2.7,
which is end-of-life since January 2020..
The minimum required version is now Python 3.6.
The last version supporting Python 2.7 was PyInstaller 3.6.


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
   hooks-config
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
