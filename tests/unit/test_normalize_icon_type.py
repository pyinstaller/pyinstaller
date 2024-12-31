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

import os
import sys
import shutil
from pathlib import Path

import pytest

from PyInstaller.building.icon import normalize_icon_type


# Runs through the normalize_icon_type tests that don't need PIL
def test_normalize_icon(monkeypatch, tmp_path):
    workpath = str(tmp_path)

    # Nonexistent image - FileNotFoundError

    icon = "this_is_not_a_file.ico"
    with pytest.raises(FileNotFoundError):
        normalize_icon_type(icon, ("ico",), "ico", workpath)

    # Native image - file path is passed through unchanged

    icon = str(Path(__file__, "../../functional/data/set_icon/pyi_icon.ico").resolve())
    ret = normalize_icon_type(icon, ("ico",), "ico", workpath)
    if ret != icon:
        pytest.fail("icon validation changed path even though the format was correct already", False)

    # Alternative image - after calling monkeypatch.setitem(sys.modules, "PIL", None): Raise the install pillow error

    monkeypatch.setitem(sys.modules, "PIL", None)
    icon = str(Path(__file__, "../../functional/data/splash/image.png").resolve())
    assert os.path.exists(icon)
    with pytest.raises(ValueError):
        normalize_icon_type(icon, ("ico",), "ico", workpath)


# Runs through the normalize_icon_type tests that DO need PIL
def test_normalize_icon_pillow(tmp_path):
    workpath = str(tmp_path)

    pytest.importorskip("PIL", reason="Needs PIL / Pillow for this test")

    # Alternative image - output is a different file with the correct suffix

    icon = str(Path(__file__, "../../functional/data/splash/image.png").resolve())
    ret = normalize_icon_type(icon, ("ico",), "ico", workpath)

    _, ret_filetype = os.path.splitext(ret)
    if ret_filetype != ".ico":
        pytest.fail("icon validation didn't convert to the right format", False)

    # A .ico which is really a mislabelled .png: should be detected and normalised

    for (i, suffix) in enumerate(["ico", "ICO"]):
        png = shutil.copy(icon, str(tmp_path / f"png-in-disguise-{i}.{suffix}"))
        normalised = normalize_icon_type(png, ("exe", "ico"), "ico", workpath)
        assert normalised != png
        assert normalize_icon_type(normalised, ("exe", "ico"), "ico", workpath) == normalised

    # Some random non-image file: Raises an image conversion error

    icon = os.path.join(tmp_path, 'pyi_icon.notanicon')
    with open(icon, "w", encoding="utf-8") as f:
        f.write("this is in fact, not an icon")

    with pytest.raises(ValueError):
        normalize_icon_type(icon, ("ico",), "ico", workpath)
