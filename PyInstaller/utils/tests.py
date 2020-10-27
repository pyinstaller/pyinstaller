#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
Decorators for skipping PyInstaller tests when specific requirements are not met.
"""

import os
import sys
import traceback
import distutils.ccompiler
import inspect
import textwrap
import shutil

import pytest
from _pytest.runner import Skipped

from PyInstaller.compat import is_win

# Wrap some pytest decorators to be consistent in tests.
parametrize = pytest.mark.parametrize
skipif = pytest.mark.skipif
xfail = pytest.mark.xfail

def _check_for_compiler():
    import tempfile, sys
    # change to some tempdir since cc.has_function() would compile into the
    # current directory, leaving garbage
    old_wd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    cc = distutils.ccompiler.new_compiler()
    if is_win:
        try:
            cc.initialize()
            has_compiler = True
        # This error is raised on Windows if a compiler can't be found.
        except distutils.errors.DistutilsPlatformError:
            has_compiler = False
    else:
        # The C standard library contains the ``clock`` function. Use that to
        # determine if a compiler is installed. This doesn't work on Windows::
        #
        #   Users\bjones\AppData\Local\Temp\a.out.exe.manifest : general error
        #   c1010070: Failed to load and parse the manifest. The system cannot
        #   find the file specified.
        has_compiler = cc.has_function('clock', includes=['time.h'])
    os.chdir(old_wd)
    # TODO: Find a way to remove the generated clockXXXX.c file, too
    shutil.rmtree(tmp)
    return has_compiler


# A decorator to skip tests if a C compiler isn't detected.
has_compiler = _check_for_compiler()
skipif_no_compiler = skipif(not has_compiler, reason="Requires a C compiler")


def skip(reason):
    """
    Unconditionally skip the currently decorated test with the passed reason.

    This decorator is intended to be called either directly as a function _or_
    indirectly as a decorator. This differs from both:

    * `pytest.skip()`, intended to be called only directly as a function.
      Attempting to call this function indirectly as a decorator produces
      extraneous ignorable messages on standard output resembling
      `SKIP [1] PyInstaller/utils/tests.py:65: could not import 'win32com'`.
    * `pytest.mark.skip()`, intended to be called only indirectly as a
      decorator. Attempting to call this decorator directly as a function
      reduces to a noop.

    Parameters
    ----------
    reason : str
        Human-readable message justifying the skipping of this test.
    """

    return skipif(True, reason=reason)


def importorskip(modname, minversion=None):
    """
    This decorator skips the currently decorated test if the module with the
    passed name is unimportable _or_ importable but of a version less than the
    passed minimum version if any.

    This decorator's name is intentionally mispelled as `importerskip` rather
    than `importerskip` to coincide with the `pytest.importorskip()` function
    internally called by this decorator.

    Parameters
    ----------
    modname : str
        Fully-qualified name of the module required by this test.
    minversion : str
        Optional minimum version of this module as a string (e.g., `3.14.15`)
        required by this test _or_ `None` if any module version is acceptable.
        Defaults to `None`.

    Returns
    ----------
    pytest.skipif
        Decorator describing these requirements if unmet _or_ the identity
        decorator otherwise (i.e., if these requirements are met).
    """

    # Defer to the eponymous function of the same name.
    try:
        pytest.importorskip(modname, minversion)
    # Silently convert expected import and syntax errors into @skip decoration.
    except Skipped as exc:
        return skip(str(exc))
    # Convert all other unexpected errors into the same decoration.
    except Exception as exc:
        # For debuggability, print a verbose stacktrace.
        print('importorskip: Exception in module "{}":'.format(modname))
        print('-' * 60)
        traceback.print_exc(file=sys.stdout)
        print('-' * 60)

        return skip(str(exc))
    # Else, this module is importable and optionally satisfies this minimum
    # version. Reduce this decoration to a noop.
    else:
        return pytest.mark.skipif(False, reason='')


def gen_sourcefile(tmpdir, source, test_id=None):
    """
    Generate a source file for testing.

    The source will be written into a file named like the
    test-function. This file will then be passed to `test_script`.
    If you need other related file, e.g. as `.toc`-file for
    testing the content, put it at at the normal place. Just mind
    to take the basnename from the test-function's name.

    :param script: Source code to create executable from. This
                   will be saved into a temporary file which is
                   then passed on to `test_script`.

    :param test_id: Test-id for parametrized tests. If given, it
                    will be appended to the script filename,
                    separated by two underscores.

    Ensure that the caller of `test_source` is in a UTF-8
    encoded file with the correct '# -*- coding: utf-8 -*-' marker.
    """
    testname = inspect.stack()[1][3]
    if test_id:
        # For parametrized test append the test-id.
        testname = testname + '__' + test_id

    # Periods are not allowed in Python module names.
    testname = testname.replace('.', '_')
    scriptfile = tmpdir / (testname + '.py')
    source = textwrap.dedent(source)
    with scriptfile.open('w', encoding='utf-8') as ofh:
        print(u'# -*- coding: utf-8 -*-', file=ofh)
        print(source, file=ofh)
    return scriptfile
