Custom modifications of 3rd party libraries
===========================================

macholib
--------

- add fixed version string to ./macholib/__init__.py::

    # For PyInstaller/lib/ define the version here, since there is no
    # package-resource.
    __version__ = '1.5.0'

- add fixed version string to ./modulegraph/__init__.py::

    # For PyInstaller/lib/ define the version here, since there is no
    # package-resource.
    __version__ = '0.9.1'

- remove the following line from ./macholib/utils.py, ./macholib/MachO.py,
  ./macholib/MachOGraph.py. Otherwise macholib complains about 
  missing altgraph module::

    from pkg_resources import require
    require("altgraph")

- remove the following line from ./macholib/utils.py::

    from modulegraph.util import *


junitxml
--------

- hacked to support ignored tests in junit xml test report.
