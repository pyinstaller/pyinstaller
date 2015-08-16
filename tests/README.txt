Tests for PyInstaller
=====================

This directory contains tests for PyInstaller:

 - ``functional`` directory contains tests where executables are created from Python scripts.
 - ``old_suite`` directory contains old structure of tests (TODO migrate all tests to a new structure)
 - ``unit`` directory contains simple unit tests

Prerequisites
-------------

In order to run the tests, you will need the following Python packages/libraries installed:

 - Mock
 - pytest

Running the Tests
-----------------

To run the tests, navigate to the root directory of the PyInstaller project, and then run the following command::

    py.test

Or, to speed up test runs by sending tests to multiple CPUs

    py.test -n NUM

Or, to run only the unit or functional tests, run the following command::

    TODO

Or, to run only a particular test suite within a file, run the
following command::

    TODO

Run all tests matching `test_ctypes_CDLL` resp. `ctypes_CDLL`::

    py.test -k test_ctypes_CDLL
    py.test -k ctypes_CDLL

Run both the onefile and ondir tests for
`test_ctypes_CDLL_find_library__nss_files`::

    py.test -k test_ctypes_CDLL_find_library__nss_files

Finally, to only run a particular test, run one of the following
commands::

    py.test -k test_ctypes_CDLL_find_library__nss_files[onedir]
    py.test -k test_ctypes_CDLL_find_library__nss_files[onefile]
