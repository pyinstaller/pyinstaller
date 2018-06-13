#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import pytest
import os

from PyInstaller.building import utils

def test_format_binaries_and_datas_not_found_raises_error(tmpdir):
    datas = [('non-existing.txt', '.')]
    tmpdir.join('existing.txt').ensure()
    # TODO Tighten test when introducing PyInstaller.exceptions
    with pytest.raises(SystemExit) as context:
        utils.format_binaries_and_datas(datas, str(tmpdir))


def test_format_binaries_and_datas_1(tmpdir):

    def _(path): return os.path.join(*path.split('/'))

    datas = [(_('existing.txt'), '.'),
             (_('other.txt'),    'foo'),
             (_('*.log'),        'logs'),
             (_('a/*.log'),      'lll'),
             (_('a/here.tex'),   '.'),
             (_('b/[abc].tex'),   'tex')]

    expected = set()
    for dest, src in (
            ('existing.txt',  'existing.txt'),
            ('foo/other.txt', 'other.txt'),
            ('logs/aaa.log',  'aaa.log'),
            ('logs/bbb.log',  'bbb.log'),
            ('lll/xxx.log',   'a/xxx.log'),
            ('lll/yyy.log',   'a/yyy.log'),
            ('here.tex',      'a/here.tex'),
            ('tex/a.tex',     'b/a.tex'),
            ('tex/b.tex',     'b/b.tex'),
    ):
        src = tmpdir.join(_(src)).ensure()
        expected.add((_(dest), str(src)))

    # add some files which are not included
    tmpdir.join(_('not.txt')).ensure()
    tmpdir.join(_('a/not.txt')).ensure()
    tmpdir.join(_('b/not.txt')).ensure()

    res = utils.format_binaries_and_datas(datas, str(tmpdir))
    assert res == expected


def test_format_binaries_and_datas_with_bracket(tmpdir):
    # See issue #2314: the filename contains brackets which are
    # interpreted by glob().

    def _(path): return os.path.join(*path.split('/'))

    datas = [(_('b/[abc].tex'),   'tex')]

    expected = set()
    for dest, src in (
            ('tex/[abc].tex',     'b/[abc].tex'),
    ):
        src = tmpdir.join(_(src)).ensure()
        expected.add((_(dest), str(src)))

    # add some files which are not included
    tmpdir.join(_('tex/not.txt')).ensure()

    res = utils.format_binaries_and_datas(datas, str(tmpdir))
    assert res == expected
