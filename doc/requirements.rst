Requirements
============

.. Keep this list in sync with the README.txt

Windows
~~~~~~~~

|PyInstaller| runs in Windows 8 or newer
(Windows 7 should work too, but is not supported).
It can create graphical windowed apps (apps that do not need a command window).

Users wishing to support older Windows versions must be aware that Python itself
has dropped support for Windows versions below 8.1. To support Windows 8.0 and 7
you must build with Python 3.8 or older and to support Windows XP you must use
Python 3.7 or older.

macOS
~~~~~~

|PyInstaller| runs on macOS 10.13 (High Sierra) or newer.
It can build graphical windowed apps (apps that do not use a terminal window).
PyInstaller builds apps that are compatible with the macOS release in
which you run it, and following releases.
It can build ``x86_64``, ``arm64`` or hybrid *universal2* binaries on macOS
machines of either architecture. See :ref:`macOS multi-arch support` for
details.

GNU/Linux
~~~~~~~~~~

|PyInstaller| requires the ``ldd`` terminal application to discover
the shared libraries required by each program or shared library.
It is typically found in the distribution-package ``glibc`` or ``libc-bin``.

It also requires the ``objdump`` terminal application to extract
information from object files
and the ``objcopy`` terminal application to append data to the
bootloader.
These are typically found in the distribution-package ``binutils``.

AIX, Solaris, FreeBSD and OpenBSD
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users have reported success running |PyInstaller| on these platforms,
but it is not tested on them.
The ``ldd`` and ``objdump`` commands are needed.

Each bundled app contains a copy of a *bootloader*,
a program that sets up the application and starts it
(see :ref:`The Bootstrap Process in Detail`).

When you install |PyInstaller| using pip_, the setup will attempt
to build a bootloader for this platform.
If that succeeds, the installation continues and |PyInstaller| is ready to use.

If the pip_ setup fails to build a bootloader,
or if you do not use pip_ to install,
you must compile a bootloader manually.
The process is described under :ref:`Building the Bootloader`.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
