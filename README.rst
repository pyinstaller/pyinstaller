PyInstaller Overview
====================

.. image:: https://img.shields.io/pypi/v/pyinstaller
   :alt: PyPI
   :target: https://pypi.org/project/pyinstaller
.. image:: https://img.shields.io/pypi/pyversions/pyinstaller
   :alt: PyPI - Python Version
   :target: https://pypi.org/project/pyinstaller
.. image:: https://img.shields.io/readthedocs/pyinstaller/stable
   :alt: Read the Docs (version)
   :target: https://pyinstaller.org
.. image:: https://img.shields.io/pypi/dm/pyinstaller
   :alt: PyPI - Downloads
   :target: https://pypistats.org/packages/pyinstaller


PyInstaller bundles a Python application and all its dependencies into a single
package. The user can run the packaged app without installing a Python
interpreter or any modules.

:Documentation: https://pyinstaller.org/
:Code:          https://github.com/pyinstaller/pyinstaller

PyInstaller reads a Python script written by you. It analyzes your code
to discover every other module and library your script needs in order to
execute. Then it collects copies of all those files -- including the active
Python interpreter! -- and puts them with your script in a single folder, or
optionally in a single executable file.


PyInstaller is tested against Windows, macOS, and GNU/Linux.
However, it is not a cross-compiler:
to make a Windows app you run PyInstaller in Windows; to make
a GNU/Linux app you run it in GNU/Linux, etc.
PyInstaller has been used successfully
with AIX, Solaris, FreeBSD and OpenBSD,
but is not tested against them as part of the continuous integration tests.


Main Advantages
---------------

- Works out-of-the-box with any Python version 3.8-3.12.
- Fully multi-platform, and uses the OS support to load the dynamic libraries,
  thus ensuring full compatibility.
- Correctly bundles the major Python packages such as numpy, PyQt5,
  PySide2, PyQt6, PySide6, wxPython, matplotlib and others out-of-the-box.
- Compatible with many 3rd-party packages out-of-the-box. (All the required
  tricks to make external packages work are already integrated.)
- Works with code signing on macOS.
- Bundles MS Visual C++ DLLs on Windows.


Installation
------------

PyInstaller is available on PyPI. You can install it through `pip`:

.. code:: bash

      pip install pyinstaller


Requirements and Tested Platforms
---------------------------------

- Python:
    - 3.8-3.12. Note that Python 3.10.0 contains a bug making it unsupportable by
      PyInstaller. PyInstaller will also not work with beta releases of Python
      3.13.
- Windows (32bit/64bit/ARM64):
    - PyInstaller should work on Windows 7 or newer, but we only officially support Windows 8+.
    - Support for Python installed from the Windows store without using virtual
      environments requires PyInstaller 4.4 or later.
- Linux:
    - GNU libc based distributions on architectures ``x86_64``, ``aarch64``,
      ``i686``, ``ppc64le``, ``s390x``.
    - musl libc based distributions on architectures ``x86_64``, ``aarch64``.
    - ldd: Console application to print the shared libraries required
      by each program or shared library. This typically can be found in
      the distribution-package `glibc` or `libc-bin`.
    - objdump: Console application to display information from
      object files. This typically can be found in the
      distribution-package `binutils`.
    - objcopy: Console application to copy and translate object files.
      This typically can be found in the distribution-package `binutils`,
      too.
    - Raspberry Pi users on ``armv5``-``armv7`` should `add piwheels as an extra
      index url <https://www.piwheels.org/>`_ then ``pip install pyinstaller``
      as usual.
- macOS (``x86_64`` or ``arm64``):
    - macOS 10.15 (Catalina) or newer.
    - Supports building ``universal2`` applications provided that your installation
      of Python and all your dependencies are also compiled ``universal2``.


Usage
-----

Basic usage is very simple, just run it against your main script:

.. code:: bash

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
- Linux on any other libc implementation/architecture combination not listed
  above.

Before using any contributed platform, you need to build the PyInstaller
bootloader. This will happen automatically when you ``pip install
pyinstaller`` provided that you have an appropriate C compiler (typically
either ``gcc`` or ``clang``) and zlib's development headers already installed.


Support
-------

- Official debugging guide: https://pyinstaller.org/en/v6.2.0/when-things-go-wrong.html
- Assorted user contributed help topics: https://github.com/pyinstaller/pyinstaller/wiki
- Web based Q&A forums: https://github.com/pyinstaller/pyinstaller/discussions
- Email based Q&A forums: https://groups.google.com/g/pyinstaller


Changes in this Release
-----------------------

You can find a detailed list of changes in this release
in the `Changelog`_ section of the manual.

.. _`manual`: https://pyinstaller.org/en/v6.2.0/
.. _`Changelog`: https://pyinstaller.org/en/v6.2.0/CHANGES.html
