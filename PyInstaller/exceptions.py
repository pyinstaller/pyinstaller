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


class ExecCommandFailed(SystemExit):
    pass


class HookError(Exception):
    """
    Base class for hook related errors.
    """
    pass


class ImportErrorWhenRunningHook(HookError):
    def __str__(self):
        return (
            "Failed to import module {0} required by hook for module {1}. Please check whether module {0} actually "
            "exists and whether the hook is compatible with your version of {1}: You might want to read more about "
            "hooks in the manual and provide a pull-request to improve PyInstaller.".format(self.args[0], self.args[1])
        )


class RemovedCipherFeatureError(SystemExit):
    def __init__(self, message):
        super().__init__(
            f"Bytecode encryption was removed in PyInstaller v6.0. {message}"
            " For the rationale and alternatives see https://github.com/pyinstaller/pyinstaller/pull/6999"
        )


class RemovedExternalManifestError(SystemExit):
    def __init__(self, message):
        super().__init__(f"Support for external executable manifest was removed in PyInstaller v6.0. {message}")


class RemovedWinSideBySideSupportError(SystemExit):
    def __init__(self, message):
        super().__init__(
            f"Support for collecting and processing WinSxS assemblies was removed in PyInstaller v6.0. {message}"
        )
