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

with relative prefix::

    from ..macholib import x
    from ..altgraph import y
    from ..modulegraph import z
    from . import ordlookup


pefile
------

Two versions of pefile are included to make PyInstaller runnable on both
Python 2 and 3. Importing pefile.py will import the correct version for
the running Python version.

- Official Python 2 version of pefile is from here:
  https://github.com/erocarrera/pefile

- There is no official port of pefile to Python 3 yet. We use this branch for PyInstaller
  https://github.com/BlackXeronic/pefile_py3

- For status of official support for Python3 see
  https://github.com/erocarrera/pefile/issues/36

Our copies of pefile.py are modified with two optimizations to speed up our specific
use-case of finding DLL names: When scanning the import table, only DLL names are
loaded and the imported symbols are not parsed; and when scanning the export table,
only "forwarded" symbols that implicitly import a DLL are returned.

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

https://bitbucket.org/ronaldoussoren/modulegraph/downloads

- TODO Use official modulegraph version when following issue is resolved and pull request merged
  https://bitbucket.org/ronaldoussoren/modulegraph/issues/28/__main__-module-being-analyzed-for-wheel
  https://bitbucket.org/ronaldoussoren/modulegraph/pull-requests/12/
  https://bitbucket.org/ronaldoussoren/modulegraph/pull-requests/13/

- add fixed version string to ./modulegraph/__init__.py::

    # For PyInstaller/lib/ define the version here, since there is no
    # package-resource.
    __version__ = '0.12.1'

