Tests for PyInstaller
=====================

This directory contains tests for PyInstaller:

- `functional` directory contains tests where executables are created from
  Python scripts.
- `unit` directory contains simple unit tests.
- `old_suite` directory contains old structure of tests (TODO migrate all tests
  to a new structure).

Prerequisites
-------------

In order to run the tests, you will need the following Python packages/libraries
installed:

- pytest
- psutil
- execnet

The easiest way to install these (and some useful pytest add-ons) is running
```
pip install -U -r tests/requirements-tools.txt
```

Running the Tests
-----------------

To run the tests, navigate to the root directory of the PyInstaller project and
run the following command:

    py.test

Or, to speed up test runs by sending tests to multiple CPUs:

    py.test -n NUM

Or, to run only the unit or functional tests, run one the following command:

    py.test tests/unit
    py.test tests/functional
    py.test tests/functional -k "not tests/functional/test_libraries.py"

Or, to run only the unit and functional tests, but not the huge library
test-suite:

    py.test tests/unit tests/functional -k "not tests/functional/test_libraries.py"


Or, to run only a particular test suite within a file, run the following
command:

    py.test tests/functional/test_basic.py -k test_pyz_as_external_file

Run all tests matching `test_ctypes_CDLL` resp. `ctypes_CDLL`:

    py.test -k test_ctypes_CDLL
    py.test -k ctypes_CDLL

Run both the onefile and ondir tests for
`test_ctypes_CDLL_find_library__nss_files`:

    py.test -k test_ctypes_CDLL_find_library__nss_files

Finally, to only run a particular test, run one of the following commands:

    py.test -k test_ctypes_CDLL_find_library__nss_files[onedir]
    py.test -k test_ctypes_CDLL_find_library__nss_files[onefile]

## Continuous Integration (CI)

Continuous integration (CI) automatically exercises all tests for all platforms
officially supported by PyInstaller.

### Python Packages

Regardless of platform or CI service, all Python packages to be tested should
be listed in `test/requirements-library.txt`. Python packages required for
exercising tests (e.g., `pytest`) should instead be listed in
`test/requirements-tools.txt`.

Both files are usual pip [requirements
files](https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format)
following the respective syntax (e.g.,
[`{package_name}>={minimum_version}`](https://pip.pypa.io/en/stable/reference/pip_install/#requirement-specifiers).
These packages will be installed with `pip` into remote testing environments
managed by third-party CI services.

Packages only available for specific version or platforms should get an appropriate
[environment
marker](https://www.python.org/dev/peps/pep-0426/#environment-markers) like
so:
```
SomeProject ==5.4 ; python_version != '3.6'
SomeProject       ; sys_platform == 'win32'
```

### Linux

The top-level `.travis.yml` file configures the Travis-CI service to remotely
test PyInstaller in an Ubuntu 12.04 (LTS) container, the most recent Linux
distribution supported by Travis-CI.

Non-Python dependencies installable through `apt-get` on Ubuntu 12.04 should be
listed as `- `-prefixed items in the `addons:` → `apt:` → `packages:` subsection
of `.travis.yml`. Since Ubuntu 12.04 provides _no_ Python 3 packages prefixed by
`python3-`, only Python 2.7 packages prefixed by `python-` are installable by
`apt-get`. Since installing only Python 2.7 packages would be useless, Python
packages should _always_ be installed by `pip` rather than `apt-get`. See
**"Python Packages"** above.

### OS X

The top-level `.travis.yml` file of a
[separate repository](https://github.com/pyinstaller/pyinstaller-osx-tests)
configures the Travis-CI service to remotely test PyInstaller in an OS X 10.9.5
virtual machine, the most recent OS X version supported by Travis-CI.

### Windows

The top-level `appveyor.yml` file configures the Appveyor service to remotely
test PyInstaller in a Windows virtual machine.

Non-Python dependencies installable through either Chocolatey (`cinst`),
PowerShell (`ps`), or WebPI (`WebpiCmd`) should be listed as `- `-prefixed items
in the `install:` section of `appveyor.yml`. See the
[official documentation](http://www.appveyor.com/docs/build-configuration#installing-additional-software)
for voluminous details.
