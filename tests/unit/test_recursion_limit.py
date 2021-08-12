#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import pytest

from PyInstaller.lib.modulegraph import modulegraph
from PyInstaller import configure
from PyInstaller import __main__ as pyi_main
from PyInstaller.compat import is_py37, is_win


@pytest.fixture
def large_import_chain(tmpdir):
    pkg = tmpdir.join('pkg')
    pkg.join('__init__.py').ensure().write('from . import a')
    mod = None
    for alpha in "abcdefg":
        if mod:
            # last module of prior sub-pkg imports this package
            mod.write("import pkg.%s" % alpha)
        subpkg = pkg.join(alpha).mkdir()
        subpkg.join('__init__.py').write('from . import %s000' % alpha)
        for num in range(250):
            # module importing its next sibling
            mod = subpkg.join("%s%03i.py" % (alpha, num))
            mod.write("from . import %s%03i" % (alpha, num + 1))
    script = tmpdir.join('script.py')
    script.write('import pkg')
    return [str(tmpdir)], str(script)


def test_recursion_to_deep(large_import_chain):
    """
    modulegraph is recursive and triggers RecursionError if nesting of imported modules is to deep.
    This can be worked around by increasing recursion limit.

    With the default recursion limit (1000), the recursion error occurs at about 115 modules, with limit 2000
    (as tested below) at about 240 modules, and with limit 5000 at about 660 modules.
    """
    if is_py37 and is_win:
        pytest.xfail("worker is know to crash for Py 3.7, 3.8 on Windows")
    path, script = large_import_chain
    mg = modulegraph.ModuleGraph(path)
    # Increase recursion limit to 5 times of the default. Given the module import chain created above
    # this still should fail.
    with pytest.raises(RecursionError):
        mg.add_script(str(script))


def test_RecursionError_prints_message(tmpdir, large_import_chain, monkeypatch):
    """
    modulegraph is recursive and triggers RecursionError if nesting of imported modules is to deep.
    Ensure an informative message is printed if RecursionError occurs.
    """
    if is_py37 and is_win:
        pytest.xfail("worker is know to crash for Py 3.7, 3.8 on Windows")
    path, script = large_import_chain

    default_args = [
        '--specpath', str(tmpdir),
        '--distpath', str(tmpdir.join("dist")),
        '--workpath', str(tmpdir.join("build")),
        '--path', str(tmpdir),
    ]  # yapf: disable

    pyi_args = [script] + default_args
    PYI_CONFIG = configure.get_config(upx_dir=None)
    PYI_CONFIG['cachedir'] = str(tmpdir)

    with pytest.raises(SystemExit) as execinfo:
        pyi_main.run(pyi_args, PYI_CONFIG)
    assert "sys.setrecursionlimit" in str(execinfo.value)
