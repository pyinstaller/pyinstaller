#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import re
import pytest
from PyInstaller.utils.tests import gen_sourcefile

test_cases = (
    (1, "onefile_depends_on_onefile"),
    (2, "onedir_depends_on_onefile"),
    (3, "onefile_depends_on_onedir"),
    (4, "onedir_depends_on_onedir"),
    (5, "onedir_and_onefile_depend_on_onedir"))

scripts = (
    '''
    # import a very simple and rarely used pure-python lib ...
    import getopt
    # ... and a module importing a shared lib
    import ssl
    print('Hello World!')
    ''',
    '''
    # a different package requiring data files
    import tkinter
    print('Hello World!')
    ''')


def patch_specfile(SPEC_DIR, num, testscript, testdep, tmp_path):
    """
    Create a spec-file containing this test's script paths.
    This allows to use some "generic" spec-files for several test-cases.
    """
    with open(os.path.join(SPEC_DIR, "test_multipackage%s.spec" % num)) as fh:
        spec = fh.read()
    spec = re.sub(r"^__testscript__\s*=.*",
                  "__testscript__ = %r" % str(testscript),
                  spec, count=1, flags=re.M)
    spec = re.sub(r"^__testdep__\s*=.*",
                  "__testdep__ = %r" % str(testdep),
                  spec, count=1, flags=re.M)
    specfile = tmp_path / ("test_multipackage%s.spec" % num)
    specfile.write_text(spec)
    return specfile


@pytest.mark.parametrize(
    "num",
    [tc[0] for tc in test_cases],
    ids=[tc[1] for tc in test_cases])
def test_spec_with_multipackage(pyi_builder_spec, tmp_path, num, SPEC_DIR):
    testscript = gen_sourcefile(tmp_path, scripts[0],
                                filename="test_multipackage.py")
    testdep = gen_sourcefile(tmp_path, scripts[0],
                             "multipackage_B.py" % num)
    specfile = patch_specfile(SPEC_DIR, num, testscript, testdep, tmp_path)
    pyi_builder_spec.test_spec(str(specfile))


@pytest.mark.parametrize(
    "num",
    [tc[0] for tc in test_cases],
    ids=[tc[1] for tc in test_cases])
def __test_spec_with_multipackage(pyi_builder_spec, num, SPEC_DIR, tmp_path):
    inspec = os.path.join(SPEC_DIR, "multipackage_%s.spec" % num)
    spec_file = temp_path / ("multipackage_%s_tkinter.spec" % num)
