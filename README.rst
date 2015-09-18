PyInstaller Overview
====================

.. image:: http://img.shields.io/travis/pyinstaller/pyinstaller/python3.svg
   :target: https://travis-ci.org/pyinstaller/pyinstaller/

.. image:: https://ci.appveyor.com/api/projects/status/t7o4swychyh94wrs/branch/python3?svg=true
   :target: https://ci.appveyor.com/project/matysek/pyinstaller/branch/python3

.. image:: http://img.shields.io/pypi/v/PyInstaller.svg
   :target: https://pypi.python.org/pypi/PyInstaller

.. image:: http://img.shields.io/pypi/dm/PyInstaller.svg
   :target: https://pypi.python.org/pypi/PyInstaller

---------------------------------------------------------------------

.. image:: https://img.shields.io/badge/docs-latest-blue.svg
   :target: http://htmlpreview.github.io/?https://github.com/pyinstaller/pyinstaller/blob/python3/doc/Manual.html
   :alt: Manual

.. image:: https://img.shields.io/badge/changes-latest-blue.svg
   :target: https://github.com/pyinstaller/pyinstaller/blob/python3/doc/CHANGES.txt
   :alt: Changelog

.. image:: https://img.shields.io/badge/IRC-pyinstalller-blue.svg
   :target: http://webchat.freenode.net/?channels=%23pyinstaller&uio=d4
   :alt: IRC


| Official website: http://www.pyinstaller.org


PyInstaller is a program that converts (packages) Python
programs into stand-alone executables, under Windows, Linux, Mac OS X,
FreeBSD, AIX and Solaris.

Its main advantages over similar tools are:

- It works out-of-the-box with any version of Python since 2.7/3.3.
- It builds smaller executables thanks to transparent compression.
- It is fully multi-platform, and uses the OS support to load the dynamic
  libraries, thus ensuring full compatibility.
- It is compatible with many 3rd-party packages out-of-the-box. This means
  that, with PyInstaller, all the required tricks to make external packages
  work are already integrated within PyInstaller itself so that there is no
  user intervention required.
- You'll never be required to look for tricks in wikis and apply custom
  modification to your files or your setup scripts.
- Libraries like PyQt5, PyQt4, PySide, matplotlib or Django matplotlib are
  fully supported, without having to handle plugins or external data files
  manually.


Requirements
------------
- Python: 
   * 2.7 or 3.3+
   * PyCrypto_ 2.4+ (only if using bytecode encryption)

- Windows (32bit/64bit):
   * Windows XP or newer.
   * pywin32_
    
- Linux (32bit/64bit)
   * ldd: Console application to print the shared libraries required
     by each program or shared library. This typically can by found in
     the distribution-package `glibc` or `libc-bin`.
   * objdump: Console application to display information from 
     object files. This typically can by found in the
     distribution-package `binutils`.

- Mac OS X (64bit):
   * Mac OS X 10.6 (Snow Leopard) or newer.


Installation
------------
PyInstaller is available on PyPI. You can install it through `pip`::

      pip install pyinstaller

Usage
-----
Basic usage is very simple, just run it against your main script::

      pyinstaller /path/to/yourscript.py

For more details, see the `manual`_.


Experimental ports
------------------
- Solaris
   * ldd
   * objdump

- AIX
   * AIX 6.1 or newer.
     Python executables created using PyInstaller on AIX 6.1 should
     work on AIX 5.2/5.3. PyInstaller will not work with statically
     linked Python libraries which has been encountered in Python 2.2
     installations on AIX 5.x.
   * ldd

- FreeBSD
   * ldd


Before using experimental ports, you need to build the PyInstaller
bootloader, as we do not ship binary packages. Download PyInstaller
sources, and build the bootloader::
     
        cd bootloader
        python ./waf configure build install

then install PyInstaller::

        python setup.py install
        
or simply use it direclty from the source (pyinstaller.py).



.. _PyCrypto: https://www.dlitz.net/software/pycrypto/
.. _pywin32: http://sourceforge.net/projects/pywin32/
.. _`manual`: http://htmlpreview.github.io/?https://github.com/pyinstaller/pyinstaller/blob/python3/doc/Manual.html
.. _`changelog`: https://github.com/pyinstaller/pyinstaller/blob/python3/doc/CHANGES.txt

