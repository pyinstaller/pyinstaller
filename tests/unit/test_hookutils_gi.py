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
