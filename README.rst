PyInstaller Overview
====================

PyInstaller bundles a Python application and all its dependencies into a single
package. The user can run the packaged app without installing a Python
interpreter or any modules.

:Documentation: https://pyinstaller.readthedocs.io/en/v4.10
:Website:       http://www.pyinstaller.org/
:Code:          https://github.com/pyinstaller/pyinstaller

PyInstaller reads a Python script written by you. It analyzes your code
to discover every other module and library your script needs in order to
execute. Then it collects copies of all those files -- including the active
Python interpreter! -- and puts them with your script in a single folder, or
optionally in a single executable file.


PyInstaller is tested against Windows, Mac OS X, and GNU/Linux.
However, it is not a cross-compiler:
to make a Windows app you run PyInstaller in Windows; to make
a GNU/Linux app you run it in GNU/Linux, etc.
PyInstaller has been used successfully
with AIX, Solaris, FreeBSD and OpenBSD,
but is not tested against them as part of the continuous integration tests.


Main Advantages
---------------

- Works out-of-the-box with any Python version 3.6-3.10.
- Fully multi-platform, and uses the OS support to load the dynamic libraries,
  thus ensuring full compatibility.
- Correctly bundles the major Python packages such as numpy, PyQt5,
  PySide2, Django, wxPython, matplotlib and others out-of-the-box.
- Compatible with many 3rd-party packages out-of-the-box. (All the required
  tricks to make external packages work are already integrated.)
- Libraries like PyQt5, PySide2, wxPython, matplotlib or Django are fully
  supported, without having to handle plugins or external data files manually.
- Works with code signing on OS X.
- Bundles MS Visual C++ DLLs on Windows.


Installation
------------

PyInstaller is available on PyPI. You can install it through `pip`::

      pip install pyinstaller


Requirements and Tested Platforms
---------------------------------

- Python: 

 - 3.6-3.10
 - tinyaes_ 1.0+ (only if using bytecode encryption).
   Instead of installing tinyaes, ``pip install pyinstaller[encryption]`` instead.

- Windows (32bit/64bit):

 - PyInstaller should work on Windows 7 or newer, but we only officially support Windows 8+.

 - Support for Python installed from the Windows store without using virtual
   environments requires PyInstaller 4.4 or later.
    
- GNU/Linux (32bit/64bit)

 - ldd: Console application to print the shared libraries required
   by each program or shared library. This typically can be found in
   the distribution-package `glibc` or `libc-bin`.
 - objdump: Console application to display information from 
   object files. This typically can be found in the
   distribution-package `binutils`.
 - objcopy: Console application to copy and translate object files.
   This typically can be found in the distribution-package `binutils`,
   too.

- Mac OS X (64bit):

 - Mac OS X 10.13 (High Sierra) or newer.


Usage
-----

Basic usage is very simple, just run it against your main script::

      pyinstaller /path/to/yourscript.py

For more details, see the `manual`_.


Untested Platforms
------------------

The following platforms have been contributed and any feedback or
enhancements on these are welcome.

- FreeBSD

 - ldd

- Solaris

 - ldd
 - objdump

- AIX

 - AIX 6.1 or newer. PyInstaller will not work with statically
   linked Python libraries.
 - ldd

- PowerPC GNU/Linux (Debian)


Before using any contributed platform, you need to build the PyInstaller
bootloader, as we do not ship binary packages. Download PyInstaller
source, and build the bootloader::
     
        cd bootloader
        python ./waf all

Then install PyInstaller::

        python setup.py install
        
or simply use it directly from the source (pyinstaller.py).


Support
-------

See http://www.pyinstaller.org/support.html for how to find help as well as
for commercial support.


Changes in this Release
-----------------------

You can find a detailed list of changes in this release
in the `Changelog`_ section of the manual.


.. _tinyaes: https://github.com/naufraghi/tinyaes-py
.. _`manual`: https://pyinstaller.readthedocs.io/en/v4.10/
.. _`Changelog`: https://pyinstaller.readthedocs.io/en/v4.10/CHANGES.html
