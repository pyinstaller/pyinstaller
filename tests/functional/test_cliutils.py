#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.cliutils import makespec

def test_maskespec_basic(tmpdir, monkeypatch):
    py = tmpdir.join('abcd.py').ensure()
    print(); print(py)
    spec = tmpdir.join('abcd.spec')
    monkeypatch.setattr('sys.argv', ['foobar', str(py)])
    # changing cwd does not work, since DEFAULT_SPECPATH is set *very* early
    monkeypatch.setattr('PyInstaller.building.makespec.DEFAULT_SPECPATH',
                        str(tmpdir))
    makespec.run()
    assert spec.exists()
    text = spec.read_text('utf-8')
    assert 'Analysis' in text
