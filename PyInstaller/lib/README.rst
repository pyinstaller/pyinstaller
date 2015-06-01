Custom modifications of 3rd party libraries
===========================================

pefile
--------

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


junitxml
--------

- hacked to support ignored tests in junit xml test report.


modulegraph
-----------

- We use customized version of ModuleGraph from
  https://bitbucket.org/leycec/modulegraph/src/1e8f74ef92a5d
  which inclused Python3-specific SWIG Support

- TODO: Use the official version when customized version is merged
  https://bitbucket.org/ronaldoussoren/modulegraph/pull-request/7/mark-namespace-packages-as-such-by/diff
