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

import pathlib
import importlib.machinery

from PyInstaller import compat
from PyInstaller.depend import analysis, bindepend
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.api import PYZ

_MODULES_DIR = pathlib.Path(__file__).parent / "modules"


def test_issue_2492(monkeypatch, tmp_path):
    # Crash if an extension module has an hidden import to ctypes (e.g. added by the hook).

    # Need to set up some values
    monkeypatch.setattr(
        'PyInstaller.config.CONF', {
            'workpath': str(tmp_path),
            'spec': str(tmp_path),
            'warnfile': str(tmp_path / 'warn.txt'),
            'dot-file': str(tmp_path / 'imports.dot'),
            'xref-file': str(tmp_path / 'imports.xref'),
            'hiddenimports': [],
            'specnm': 'issue_2492_script',
            'code_cache': dict(),
        }
    )
    # Speedup: avoid analyzing base_library.zip
    monkeypatch.setattr(analysis, 'PY3_BASE_MODULES', [])

    script = tmp_path / 'script.py'
    script.write_text("import _struct", encoding='utf-8')

    # Create a hook
    (tmp_path / 'hook-_struct.py').write_text("hiddenimports = ['ctypes']", encoding='utf-8')
    Analysis([str(script)], hookspath=[str(tmp_path)], excludes=['encodings', 'pydoc', 'xml', 'distutils'])


def test_issue_5131(monkeypatch, tmp_path):
    """
    While fixing the endless recursion when the package's __init__ module is an extension (see
    tests/unit/test_modulegraph_more.py::package_init_is_extension_*), another error occurred:
    PyInstaller.building._utils._load_code() tried to complete the source code for extension module - triggered by
    PYZ.assemble(), which is collecting all source files - caused by this being marked as "PYMODULE" in the TOC.
    """
    def get_imports(*args, **kwargs):
        # Our faked binary does not match the expected file-format for all platforms, thus the resp. code might crash.
        # Simply ignore this.
        try:
            return orig_get_imports(*args, **kwargs)
        except Exception:
            return []

    orig_get_imports = bindepend.get_imports
    monkeypatch.setattr(bindepend, "get_imports", get_imports)

    # On macOS, we need to similarly override `osxutils.get_macos_sdk_version`.
    if compat.is_darwin:
        from PyInstaller.utils import osx as osxutils

        def get_macos_sdk_version(*args, **kwargs):
            try:
                return orig_get_macos_sdk_version(*args, **kwargs)
            except Exception:
                return (10, 9, 0)  # Minimum version expected by check in Analysis.

        orig_get_macos_sdk_version = osxutils.get_macos_sdk_version
        monkeypatch.setattr(osxutils, "get_macos_sdk_version", get_macos_sdk_version)

    # Set up fake CONF for Analysis
    monkeypatch.setattr(
        'PyInstaller.config.CONF', {
            'workpath': str(tmp_path),
            'spec': str(tmp_path),
            'warnfile': str(tmp_path / 'warn.txt'),
            'dot-file': str(tmp_path / 'imports.dot'),
            'xref-file': str(tmp_path / 'imports.xref'),
            'hiddenimports': [],
            'specnm': 'issue_5131_script',
            'code_cache': dict(),
        }
    )

    # Speedup: avoid analyzing base_library.zip
    monkeypatch.setattr(analysis, 'PY3_BASE_MODULES', [])

    pkg = tmp_path / 'mypkg'
    pkg.mkdir()

    init = pkg / f"__init__{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    init.write_bytes(b'\0\0\0\0\0\0\0\0\0\0\0\0' * 20)

    script = tmp_path / 'script.py'
    script.write_text("import mypkg", encoding='utf-8')

    a = Analysis([str(script)], excludes=['encodings', 'pydoc', 'xml', 'distutils'])
    PYZ(a.pure)


def test_issue_4141(pyi_builder):
    extra_path = _MODULES_DIR / 'pyi_issue_4141'
    pyi_builder.test_script(
        'pyi_issue_4141.py', app_name="main", run_from_path=True, pyi_args=['--path', str(extra_path)]
    )


def test_5734():
    """
    In a regression this will raise a:
        FileNotFoundError: [Errno 2] No such file or directory: b'liblibc.a'
    on some Linux/gcc combinations.
    """
    from PyInstaller.depend.utils import _resolveCtypesImports
    _resolveCtypesImports(["libc"])


def test_5797(pyi_builder):
    """
    Ensure that user overriding os and/or sys (using them as variables) in the global namespace does not affect
    PyInstaller's ctype hooks, installed during bootstrap, which is scenario of the issue #5797.
    """
    pyi_builder.test_source(
        """
        import ctypes

        # Overwrite sys and os in global namespace
        sys = 'watever'
        os = 'something'

        # Use a ctypes.CDLL, which in turn calls _frozen_name() from PyInstaller's ctypes bootstrap hooks.
        try:
            ctypes.CDLL('nonexistent')
        except Exception as e:
            # We expect PyInstallerImportError to be raised
            exception_name = type(e).__name__
            assert exception_name == 'PyInstallerImportError', f"Unexpected exception type: {exception_name}"
        """
    )
