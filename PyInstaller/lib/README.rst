Custom modifications of 3rd party libraries
===========================================

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
