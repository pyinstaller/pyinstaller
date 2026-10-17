Tests for PyInstaller
=====================

This directory contains PyInstaller's test suite:

- `unit` directory contains small, fast tests for individual PyInstaller modules.
- `functional` directory contains end-to-end tests that build and run real executables.

The `unit/test_modulegraph` directory contains the vendored test-suite of the `modulegraph`
project. Changes there should generally be made upstream.

Prerequisites
-------------

Install PyInstaller in development mode, then pick a set of test requirements:

```
pip install -e .

# Base test tools only (fast; functional tests that need 3rd-party libraries skip):
pip install -r tests/requirements-base.txt

# For the full test suite, also install the library requirements:
pip install -r tests/requirements-libraries.txt
```

The requirements files are layered:

- `requirements-base.txt` — the test framework (`pytest`, `pytest-xdist`, ...) and the few
  packages needed by basic tests. Also used for pre-release Python versions, where wheels
  for heavier packages may not be available yet.
- `requirements-tools.txt` — base requirements plus packages needed by some basic tests.
- `requirements-libraries.txt` — the full set of third-party libraries exercised by the
  functional tests. Most entries are exactly pinned and updated by the pyup bot; a few
  packages that only some test environments can use are deliberately left unpinned with a
  lower bound.

Running the Tests
-----------------

To run the tests, navigate to the root directory of the PyInstaller project and run the
following command:

    pytest

Or, to speed up test runs by sending tests to multiple CPUs: (requires pytest-xdist)

    pytest -n auto

To run only the unit or functional tests:

    pytest tests/unit
    pytest tests/functional

To run the unit and functional tests, but not the huge library test-suite, either ignore
that file by path:

    pytest tests/unit tests/functional --ignore=tests/functional/test_libraries.py

or deselect it by name:

    pytest tests/unit tests/functional -k "not test_libraries"

Note that `-k` matches test, class and module *names* (the module keyword is the file's
basename, `test_libraries`), not file paths — so `-k "not tests/functional/test_libraries.py"`
matches nothing and therefore excludes nothing.

To run only a particular test suite within a file:

    pytest tests/functional/test_basic.py -k test_pyz_as_external_file

Run all tests matching `test_ctypes_CDLL` resp. `ctypes_CDLL`:

    pytest -k test_ctypes_CDLL
    pytest -k ctypes_CDLL

Finally, to only run a particular test, run:

    pytest -k "test_ctypes_CDLL_find_library__nss_files and onedir"

The functional tests are automatically parametrized over the `onedir` and `onefile`
application modes; the last command above selects just one of the two.

Test data layout (functional tests)
-----------------------------------

The `functional` tests share a common set of fixtures (see `tests/conftest.py`):

- `scripts/` — runnable scripts referenced by name, e.g.
  `pyi_builder.test_script('pyi_codecs.py')`. Tests built from inline source use
  `pyi_builder.test_source(...)` instead; the generated script file is named after the test.
- `modules/` — importable helper packages, put on the build's module search path by the
  builder itself.
- `data/<test function name>/` — data files, copied to the build directory by the `data_dir`
  fixture, which copies the directory matching the name of the test function.
- `specs/` — .spec files referenced by `pyi_builder_spec.test_spec()`.
- `logs/` — reference `.toc` archives. If a `<exe name>.toc` file exists for the executable
  that a test produced, the contents of the frozen application are compared against it.

Continuous Integration (CI)
---------------------------

Continuous integration (see `.github/workflows/ci.yml`) exercises all tests for all
platforms officially supported by PyInstaller: Windows, macOS, and GNU/Linux (including
musl-based distributions, Cygwin, and AppImage packaging).

Jobs that install `requirements-libraries.txt` run the extensive suite; the remaining jobs
run the base suite only, where library-dependent tests skip automatically. All test
requirements must therefore be declared in the requirements files listed above so that CI
environments stay self-describing.

Platform-specific tests are marked with the `darwin`, `linux`, or `win32` pytest markers and
only run on the corresponding platform.
