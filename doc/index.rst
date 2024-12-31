==================
PyInstaller Manual
==================

:Version: |PyInstallerVersion|
:Homepage: `<https://pyinstaller.org/>`_
:Contact: pyinstaller@googlegroups.com
:Authors: David Cortesi, based on structure by Giovanni Bajo & William Caban, based on Gordon McMillan's manual
:Copyright: This document has been placed in the public domain.


PyInstaller bundles a Python application and all its dependencies into a single package.
The user can run the packaged app without installing a Python interpreter or any modules.
PyInstaller supports Python 3.8 and newer, and correctly bundles many major Python packages
such as numpy, matplotlib, PyQt, wxPython, and others.

PyInstaller is tested against Windows, macOS, and Linux.
However, it is not a cross-compiler; to make a Windows app you run PyInstaller on Windows,
and to make a Linux app you run it on Linux, etc.
x
PyInstaller has been used successfully with AIX, Solaris, FreeBSD and OpenBSD but testing
against them is not part of our continuous integration tests, and the development team offers
no guarantee (all code for these platforms comes from external contributions)
that PyInstaller will work on these platforms or that they will continue to be supported.


Quickstart
__________

Make sure you have the :ref:`PyInstaller Requirements` installed, and then install PyInstaller from PyPI:

.. code-block:: bash

    pip install -U pyinstaller

Open a command prompt/shell window, and navigate to the directory where your `.py` file is
located, then build your app with the following command:

.. code-block:: bash

    pyinstaller your_program.py

Your bundled application should now be available in the `dist` folder.

.. note::

    See :ref:`pyinstaller_not_in_path` if you get some kind of *pyinstaller
    command not found* error.


Contents:
_________

.. toctree::
   :maxdepth: 2

   requirements
   license
   contributing
   installation
   operating-mode
   usage
   common-issues-and-pitfalls
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
