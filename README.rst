.. image:: http://www.pyinstaller.org/chrome/site/logo.png
   :align: right
   :target: http://www.pyinstaller.org

PyInstaller
===========
.. image:: http://img.shields.io/pypi/v/PyInstaller.png
   :target: https://pypi.python.org/pypi/PyInstaller

.. image:: http://img.shields.io/pypi/dm/PyInstaller.png
   :target: https://pypi.python.org/pypi/PyInstaller

.. image:: http://img.shields.io/travis/pyinstaller/pyinstaller.png
   :target: https://travis-ci.org/pyinstaller/pyinstaller/


| Official website: http://www.pyinstaller.org
| Full manual: http://pythonhosted.org/PyInstaller
| Full changelog: `changelog`_


Requirements
------------
- Python: 
   * 2.6 - 2.7 (Python 3 is not supported)
   * PyCrypto_ 2.4+ (only if using bytecode encryption)

- Windows (32bit/64bit):
   * Windows XP or newer.
   * pywin32_ when using Python 2.6+
    
- Linux (32bit/64bit)
   * ldd: Console application to print the shared libraries required
     by each program or shared library. This typically can by found in
     the distribution-package `glibc` or `libc-bin`.
   * objdump: Console application to display information from 
     object files. This typically can by found in the
     distribution-package `binutils`.

- Mac OS X (32/64bit):
   * Mac OS X 10.6 (Tiger) or newer.


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
.. _`manual`: http://pythonhosted.org/PyInstaller
.. _`changelog`: https://github.com/pyinstaller/pyinstaller/blob/develop/doc/CHANGES.txt

