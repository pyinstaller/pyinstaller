#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
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


@pytest.fixture
def large_import_chain(tmp_path):
    # Create package directory
    pkg = tmp_path / 'pkg'
    pkg.mkdir()
    # Create pkg/__init__py that imports first sub-package (a)
    (pkg / '__init__.py').write_text("from . import a", encoding='utf-8')
    # Create sub-packages
    mod = None
    for alpha in "abcdefg":
        # Overwrite last module of previous sub-package to import this sub-package.
        if mod:
            mod.write_text(f"import pkg.{alpha}", encoding='utf-8')
        # Create sub-package
        subpkg = pkg / alpha
        subpkg.mkdir()
        # Create sub-package's __init__.py, which imports first module.
        (subpkg / '__init__.py').write_text(f"from . import {alpha}000", encoding='utf-8')
        # Create modules; each module imports its next sibling (except the very last one, which we overwrite at the
        # start of next loop iteration).
        for num in range(250):
            mod = subpkg / f"{alpha}{num:03}.py"
            mod.write_text(f"from . import {alpha}{num + 1:03}", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text('import pkg', encoding='utf-8')

    return [str(tmp_path)], str(script)


def test_recursion_too_deep(large_import_chain):
    """
    modulegraph is recursive and triggers RecursionError if nesting of imported modules is too deep.
    This can be worked around by increasing recursion limit.

    With the default recursion limit (1000), the recursion error occurs at about 115 modules, with limit 2000
    (as tested below) at about 240 modules, and with limit 5000 at about 660 modules.
    """
    path, script = large_import_chain
    mg = modulegraph.ModuleGraph(path)
    # Increase recursion limit to 5 times of the default. Given the module import chain created above
    # this still should fail.
    with pytest.raises(RecursionError):
        mg.add_script(script)


def test_RecursionError_prints_message(tmp_path, large_import_chain, monkeypatch):
    """
    modulegraph is recursive and triggers RecursionError if nesting of imported modules is too deep.
    Ensure an informative message is printed if RecursionError occurs.
    """
    path, script = large_import_chain

    default_args = [
        '--specpath', str(tmp_path),
        '--distpath', str(tmp_path / 'dist'),
        '--workpath', str(tmp_path / 'build'),
        '--path', str(tmp_path),
    ]  # yapf: disable

    pyi_args = [script, *default_args]
    PYI_CONFIG = configure.get_config()
    PYI_CONFIG['cachedir'] = str(tmp_path)

    with pytest.raises(SystemExit) as execinfo:
        pyi_main.run(pyi_args, PYI_CONFIG)
    assert "sys.setrecursionlimit" in str(execinfo.value)
