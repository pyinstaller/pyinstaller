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
 - Nose2

On Debian/Ubuntu you can simple install the python3-mock and python3-nose2 packages. Most other distributions will also have these
packages. On Windows and Mac OS X you will need to use ``pip`` or ``easy_install`` to install these packages.

Running the Tests
-----------------

To run the tests, navigate to the root directory of the PyInstaller project, and then run the following command::

    nose2 -s tests

Or, to run only the unit or freeze tests, run the following command::

    TODO

Or, to run only a particular test suite within a file, run the following command::

    TODO

Finally, to only run a particular test, run the following command::

    TODO
