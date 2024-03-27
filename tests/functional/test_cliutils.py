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

from PyInstaller.utils.cliutils import makespec


def test_maskespec_basic(tmpdir, monkeypatch):
    py = tmpdir.join('abcd.py').ensure()
    print()
    print(py)
    spec = tmpdir.join('abcd.spec')
    monkeypatch.setattr('sys.argv', ['foobar', str(py)])
    # changing cwd does not work, since DEFAULT_SPECPATH is set *very* early
    monkeypatch.setattr('PyInstaller.building.makespec.DEFAULT_SPECPATH', str(tmpdir))
    makespec.run()
    assert spec.exists()
    text = spec.read_text('utf-8')
    assert 'Analysis' in text


def test_makespec_splash(tmpdir, monkeypatch):
    py = tmpdir.join('with_splash.py').ensure()
    print()
    print(py)
    spec = tmpdir.join('with_splash.spec')
    monkeypatch.setattr('sys.argv', ['foobar', '--splash', 'image.png', str(py)])
    monkeypatch.setattr('PyInstaller.building.makespec.DEFAULT_SPECPATH', str(tmpdir))
    makespec.run()
    assert spec.exists()
    text = spec.read_text('utf-8')
    assert 'Splash' in text


@pytest.mark.win32
def test_makespec_path_sep_normalisation(tmp_path, monkeypatch):
    args = [
        "",
        r"foo'\bar.py",
        r"--splash=foo'\bar.png",
        r"--add-data=foo'\bar:a\b",
        r"--path=foo'\bar",
        r"--icon=foo'\bar.png",
        r"--additional-hooks-dir=foo'\bar",
        r"--runtime-hook=foo'\bar",
        r"--upx-exclude=foo'\bar",
    ]
    monkeypatch.setattr('sys.argv', args)
    monkeypatch.setattr('PyInstaller.building.makespec.DEFAULT_SPECPATH', str(tmp_path))
    makespec.run()
    spec_contents = (tmp_path / "bar.spec").read_text("utf-8")
    # All backslashes should have been converted to forward slashes
    assert "\\" not in spec_contents
    # Check for syntax errors (most likely from bogus quotes)
    compile(spec_contents, "", "exec")
