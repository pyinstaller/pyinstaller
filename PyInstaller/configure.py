#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Configure PyInstaller for the current Python installation.
"""

import os

from PyInstaller import compat
from PyInstaller import log as logging
from PyInstaller.compat import is_darwin, is_win

logger = logging.getLogger(__name__)


def test_UPX(config, upx_dir):
    logger.debug('Testing for UPX ...')
    cmd = "upx"
    if upx_dir:
        cmd = os.path.normpath(os.path.join(upx_dir, cmd))

    hasUPX = 0
    try:
        vers = compat.exec_command(cmd, '-V', raise_enoent=True).strip().splitlines()
        if vers:
            v = vers[0].split()[1]
            try:
                # v = "3.96-git-d7ba31cab8ce"
                v = v.split("-")[0]
            except Exception:
                pass
            hasUPX = tuple(map(int, v.split(".")))
            if is_win and hasUPX < (1, 92):
                logger.error('UPX is too old! Python 2.4 under Windows requires UPX 1.92+.')
                hasUPX = 0
    except Exception as e:
        if isinstance(e, OSError) and e.errno == 2:
            # No such file or directory
            pass
        else:
            logger.info('An exception occured when testing for UPX:')
            logger.info('  %r', e)
    if hasUPX:
        is_available = 'available'
    else:
        is_available = 'not available'
    logger.info('UPX is %s.', is_available)
    config['hasUPX'] = hasUPX
    config['upx_dir'] = upx_dir


def _get_pyinst_cache_dir():
    old_cache_dir = None
    if compat.getenv('PYINSTALLER_CONFIG_DIR'):
        cache_dir = compat.getenv('PYINSTALLER_CONFIG_DIR')
    elif is_win:
        cache_dir = compat.getenv('LOCALAPPDATA')
        if not cache_dir:
            cache_dir = os.path.expanduser('~\\Application Data')
    elif is_darwin:
        cache_dir = os.path.expanduser('~/Library/Application Support')
    else:
        # According to XDG specification: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
        old_cache_dir = compat.getenv('XDG_DATA_HOME')
        if not old_cache_dir:
            old_cache_dir = os.path.expanduser('~/.local/share')
        cache_dir = compat.getenv('XDG_CACHE_HOME')
        if not cache_dir:
            cache_dir = os.path.expanduser('~/.cache')
    cache_dir = os.path.join(cache_dir, 'pyinstaller')
    # Move old cache-dir, if any, to new location.
    if old_cache_dir and not os.path.exists(cache_dir):
        old_cache_dir = os.path.join(old_cache_dir, 'pyinstaller')
        if os.path.exists(old_cache_dir):
            parent_dir = os.path.dirname(cache_dir)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            os.rename(old_cache_dir, cache_dir)
    return cache_dir


def get_config(upx_dir, **kw):
    config = {}
    test_UPX(config, upx_dir)
    config['cachedir'] = _get_pyinst_cache_dir()

    return config
