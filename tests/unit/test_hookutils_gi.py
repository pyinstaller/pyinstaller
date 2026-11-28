#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import subprocess

import pytest

from PyInstaller.config import CONF
from PyInstaller.utils.hooks import gi
from PyInstaller.utils.hooks.gi import GiModuleInfo


def test_module_info():
    module_info = GiModuleInfo("MyModule", "1.0")

    assert module_info.name == "MyModule"
    assert module_info.version == "1.0"


def test_module_info_with_versions():
    hook_api = hook_api_for_module_version("MyModule", "2.0")

    module_info = GiModuleInfo("MyModule", "1.0", hook_api)

    assert module_info.name == "MyModule"
    assert module_info.version == "2.0"


@pytest.mark.parametrize("use_standard_dir", [True, False])
def test_gir_library_path_fix(tmp_path, monkeypatch, use_standard_dir):
    prefix = tmp_path / "prefix"
    typelib = prefix / "lib" / "custom" / "girepository-1.0" / "MyModule-1.0.typelib"
    data_dirs = [prefix / "share" / "missing", prefix / "share" / "custom"]
    gir_name = "MyModule-1.0.gir"
    gir_dir = (prefix / "share" if use_standard_dir else data_dirs[1]) / "gir-1.0"
    gir_dir.mkdir(parents=True)
    (gir_dir / gir_name).write_text('<namespace shared-library="/prefix/lib/libfoo.dylib">\n', encoding="utf-8")
    workpath = tmp_path / "build"
    workpath.mkdir()

    monkeypatch.setattr(gi.compat, "is_darwin", True)
    monkeypatch.setattr(gi.compat, "base_prefix", str(prefix))
    monkeypatch.setattr(gi, "get_glib_system_data_dirs", lambda: list(map(str, data_dirs)))
    monkeypatch.setitem(CONF, "workpath", str(workpath))
    commands = []

    class Compiler:
        def __init__(self, command):
            commands.append(command)

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", Compiler)

    output_file = str(workpath / typelib.name)
    assert gi.gir_library_path_fix(typelib) == (output_file, "gi_typelibs")
    assert commands == [("g-ir-compiler", str(workpath / gir_name), "-o", output_file)]
    rewritten_gir = (workpath / gir_name).read_text(encoding="utf-8")
    assert rewritten_gir == '<namespace shared-library="@loader_path/libfoo.dylib">\n'


def hook_api_for_module_version(module, version):
    class hook_api_stub:
        class analysis:
            hooksconfig = {
                "gi": {
                    "module-versions": {
                        module: version,
                    }
                }
            }

    return hook_api_stub
