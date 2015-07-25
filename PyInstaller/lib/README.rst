Custom modifications of 3rd party libraries
===========================================

NOTE: PyInstaller does not extend PYTHONPATH (sys.path) with this directory
that contains bundled 3rd party libraries.

Some users complained that PyInstaller failed because their apps were using
too old versions of some libraries that PyInstaller uses too and that's why
extending sys.path was dropped.

All libraries are tweaked to be importable as::

    from PyInstaller.lib.LIB_NAME import xyz

In libraries replace imports like::

    from macholib import x
    from altgraph import y
    from modulegraph import z
    import ordlookup

with PyInstaller prefix::

    from PyInstaller.lib.macholib import x
    from PyInstaller.lib.altgraph import y
    from PyInstaller.lib.modulegraph import z
    import PyInstaller.lib.ordlookup as ordlookup


pefile
--------

Two versions of pefile are included to make PyInstaller runnable on both
Python 2 and 3. Importing pefile.py will import the correct version for
the running Python version.

- Official Python 2 version of pefile is from here:
  https://github.com/erocarrera/pefile

- There is no official port of pefile to Python 3 yet. We use this branch for PyInstaller
  https://github.com/BlackXeronic/pefile_py3

- For status of official support for Python3 see
  https://code.google.com/p/pefile/issues/detail?id=36


macholib
--------

- add fixed version string to ./macholib/__init__.py::

    # For PyInstaller/lib/ define the version here, since there is no
    # package-resource.
    __version__ = '1.7.0'

- add fixed version string to ./altgraph/__init__.py::

    # For PyInstaller/lib/ define the version here, since there is no
    # package-resource.
    __version__ = '0.12'


modulegraph
-----------

- We use customized version of ModuleGraph from
  https://bitbucket.org/leycec/modulegraph/src/1e8f74ef92a5d
  which inclused Python3-specific SWIG Support

- TODO: Use the official version when customized version is merged
  https://bitbucket.org/ronaldoussoren/modulegraph/pull-request/7/mark-namespace-packages-as-such-by/diff
