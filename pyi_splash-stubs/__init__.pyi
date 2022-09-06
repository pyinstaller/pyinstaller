# -----------------------------------------------------------------------------
# Copyright (c) 2022-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

# https://pyinstaller.org/en/stable/advanced-topics.html#module-pyi_splash
# https://github.com/pyinstaller/pyinstaller/blob/develop/PyInstaller/fake-modules/pyi_splash.py
__all__ = ["is_alive", "close", "update_text"]


def is_alive() -> bool:
    ...


def update_text(msg: str) -> None:
    ...


def close() -> None:
    ...
