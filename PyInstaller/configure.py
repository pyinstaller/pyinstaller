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
"""
Configure PyInstaller for the current Python installation.
"""

import os
import subprocess

from PyInstaller import compat
from PyInstaller import log as logging

logger = logging.getLogger(__name__)


def _check_upx_availability(upx_dir):
    logger.debug('Testing UPX availability ...')

    upx_exe = "upx"
    if upx_dir:
        upx_exe = os.path.normpath(os.path.join(upx_dir, upx_exe))

    # Check if we can call `upx -V`.
    try:
        output = subprocess.check_output(
            [upx_exe, '-V'],
            stdin=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        )
    except Exception:
        logger.debug('UPX is not available.')
        return False

    # Read the first line to display version string
    try:
        version_string = output.splitlines()[0]
    except IndexError:
        version_string = 'version string unavailable'

    logger.debug('UPX is available: %s', version_string)
    return True


def _get_pyinstaller_cache_dir():
    old_cache_dir = None
    if compat.getenv('PYINSTALLER_CONFIG_DIR'):
        cache_dir = compat.getenv('PYINSTALLER_CONFIG_DIR')
    elif compat.is_win:
        cache_dir = compat.getenv('LOCALAPPDATA')
        if not cache_dir:
            cache_dir = os.path.expanduser('~\\Application Data')
    elif compat.is_darwin:
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

    config['cachedir'] = _get_pyinstaller_cache_dir()
    config['upx_dir'] = upx_dir
    config['hasUPX'] = _check_upx_availability(upx_dir)

    return config
