.. _feature notes:

===============================
Notes about specific Features
===============================

This sections describes details about specific features. For a
:ref:`full list of features <website:features>`
please refer to the website.


Ctypes Dependencies
=========================

Ctypes is a foreign function library for Python, that allows calling functions
present in shared libraries. Those libraries are not imported as Python
packages, because they are not picked up via Python imports: their path is
passed to ctypes instead, which deals with the shared library directly; this
caused <1.4 PyInstaller import detect machinery to miss those libraries,
failing the goal to build self-contained PyInstaller executables::

  from ctypes import *
  # This will pass undetected under PyInstaller detect machinery,
  # because it's not a direct import.
  handle = CDLL("/usr/lib/library.so")
  handle.function_call()


Solution in |PyInstaller|
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyInstaller contains a pragmatic implementation of Ctypes dependencies: it
will search for simple standard usages of ctypes and **automatically** track
and bundle the referenced libraries. The following usages will be correctly
detected::

  CDLL("library.so")
  WinDLL("library.so")
  ctypes.DLL("library.so")
  cdll.library # Only valid under Windows - a limitation of ctypes, not PyInstaller's
  windll.library # Only valid under Windows - a limitation of ctypes, not PyInstaller's
  cdll.LoadLibrary("library.so")
  windll.LoadLibrary("library.so")


More in detail, the following restrictions apply:

* **only libraries referenced by bare filenames (e.g. no leading paths) will
  be handled**; handling absolute paths would be impossible without modifying
  the bytecode as well (remember that while running frozen, ctypes would keep
  searching the library at that very absolute location, whose presence on the
  host system nobody can guarantee), and relative paths handling would require
  recreating in the frozen executable the same hierarchy of directories
  leading to the library, in addition of keeping track of which the current
  working directory is;

* **only library paths represented by a literal string will be detected and
  included in the final executable**: PyInstaller import detection works by
  inspecting raw Python bytecode, and since you can pass the library path to
  ctypes using a string (that can be represented by a literal in the code, but
  also by a variable, by the return value of an arbitrarily complex function,
  etc...), it's not reasonably possible to detect **all** ctypes dependencies;

* **only libraries referenced in the same context of ctypes' invocation will
  be handled**.

We feel that it should be enough to cover most ctypes' usages, with little or
no modification required in your code.

Gotchas
~~~~~~~~~~~~~~~

The ctypes detection system at :ref:`Analysis time <spec-file operations>`
is based on ``ctypes.util.find_library()``.
This means that you have to make sure
that while performing ``Analysis`` and running frozen,
all the environment values ``find_library()`` uses to search libraries
are aligned to those when running un-frozen.
Examples include using ``LD_LIBRARY_PATH`` or ``DYLD_LIBRARY_PATH`` to
widen ``find_library()`` scope.


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
