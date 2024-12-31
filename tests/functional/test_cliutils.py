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

from PyInstaller.utils.cliutils import makespec


def test_maskespec_basic(tmp_path, monkeypatch):
    py_file = tmp_path / 'abcd.py'
    py_file.touch()

    monkeypatch.setattr('sys.argv', ['foobar', str(py_file)])
    # changing cwd does not work, since DEFAULT_SPECPATH is set *very* early
    monkeypatch.setattr('PyInstaller.building.makespec.DEFAULT_SPECPATH', str(tmp_path))
    makespec.run()

    spec_file = tmp_path / 'abcd.spec'
    assert spec_file.exists()
    spec_text = spec_file.read_text(encoding='utf-8')
    assert 'Analysis' in spec_text


def test_makespec_splash(tmp_path, monkeypatch):
    py_file = tmp_path / 'with_splash.py'
    py_file.touch()

    monkeypatch.setattr('sys.argv', ['foobar', '--splash', 'image.png', str(py_file)])
    monkeypatch.setattr('PyInstaller.building.makespec.DEFAULT_SPECPATH', str(tmp_path))
    makespec.run()

    spec_file = tmp_path / 'with_splash.spec'
    assert spec_file.exists()
    spec_text = spec_file.read_text('utf-8')
    assert 'Splash' in spec_text
