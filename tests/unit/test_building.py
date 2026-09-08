#-----------------------------------------------------------------------------
# Copyright (c) 2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import pytest

from PyInstaller import config
from PyInstaller.building import build_main


@pytest.mark.parametrize('cache_name, work_name', [('cache', 'work'), ('cache[0]', 'work'), ('cache', 'work[0]')])
@pytest.mark.parametrize('clean_build', [False, True])
def test_clean_build_literal_paths(tmp_path, monkeypatch, cache_name, work_name, clean_build):
    spec = tmp_path / 'empty.spec'
    spec.write_text('', encoding='utf-8')
    cache_dir = tmp_path / cache_name
    work_root = tmp_path / work_name
    # build() appends the spec basename to the requested work directory.
    work_dir = work_root / spec.stem

    for directory in (cache_dir, work_dir):
        directory.mkdir(parents=True)
        (directory / 'old-file').touch()
        (directory / 'old-dir').mkdir()
        (directory / 'old-dir' / 'nested-file').touch()
        (directory / '.hidden-file').touch()

    # These paths would match the unescaped bracket expressions.
    neighbors = (tmp_path / 'cache0', tmp_path / 'work0' / spec.stem)
    for directory in neighbors:
        directory.mkdir(parents=True)
        (directory / 'keep-file').touch()

    monkeypatch.setattr(config, 'CONF', {'cachedir': str(cache_dir)})
    build_main.build(str(spec), str(tmp_path / 'dist'), str(work_root), clean_build)

    for directory in (cache_dir, work_dir):
        assert directory.is_dir()
        assert (directory / 'old-file').exists() is not clean_build
        assert (directory / 'old-dir').exists() is not clean_build
        # Preserve the existing glob behavior for hidden files.
        assert (directory / '.hidden-file').is_file()
    for directory in neighbors:
        assert (directory / 'keep-file').is_file()
