#! /usr/bin/env python
#
# Configure PyInstaller for the current Python installation.
#
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
import os
import sys
import shutil
import re
import time
import inspect

from PyInstaller import HOMEPATH, PLATFORM
from PyInstaller import is_win, is_unix, is_darwin, is_py24, get_version

import PyInstaller.build as build
import PyInstaller.compat as compat

import PyInstaller.log as logging
import PyInstaller.depend.modules
import PyInstaller.depend.imptracker

logger = logging.getLogger('PyInstaller.configure')


def test_Crypt(config):
    # TODO: disabled for now
    config["useCrypt"] = 0
    return

    #Crypt support. We need to build the AES module and we'll use distutils
    # for that. FIXME: the day we'll use distutils for everything this will be
    # a solved problem.
    logger.info("trying to build crypt support...")
    from distutils.core import run_setup
    cwd = os.getcwd()
    args = sys.argv[:]
    try:
        os.chdir(os.path.join(HOMEPATH, "source", "crypto"))
        dist = run_setup("setup.py", ["install"])
        if dist.have_run.get("install", 0):
            config["useCrypt"] = 1
            logger.info("... crypto support available")
        else:
            config["useCrypt"] = 0
            logger.info("... error building crypto support")
    finally:
        os.chdir(cwd)
        sys.argv = args


def test_RsrcUpdate(config):
    config['hasRsrcUpdate'] = 0
    if not is_win:
        return
    # only available on windows
    logger.info("Testing for ability to set icons, version resources...")
    try:
        import win32api
        from PyInstaller.utils import icon, versioninfo
    except ImportError, detail:
        logger.info('... resource update unavailable - %s', detail)
        return

    test_exe = os.path.join(HOMEPATH, 'support', 'loader', PLATFORM, 'runw.exe')
    if not os.path.exists(test_exe):
        config['hasRsrcUpdate'] = 0
        logger.error('... resource update unavailable - %s not found', test_exe)
        return

    # The test_exe may be read-only
    # make a writable copy and test using that
    rw_test_exe = os.path.join(compat.getenv('TEMP'), 'me_test_exe.tmp')
    shutil.copyfile(test_exe, rw_test_exe)
    try:
        hexe = win32api.BeginUpdateResource(rw_test_exe, 0)
    except:
        logger.info('... resource update unavailable - win32api.BeginUpdateResource failed')
    else:
        win32api.EndUpdateResource(hexe, 1)
        config['hasRsrcUpdate'] = 1
        logger.info('... resource update available')
    os.remove(rw_test_exe)


def test_UPX(config, upx_dir):
    logger.debug('Testing for UPX ...')
    cmd = "upx"
    if upx_dir:
        cmd = os.path.normpath(os.path.join(upx_dir, cmd))

    hasUPX = 0
    try:
        vers = compat.exec_command(cmd, '-V').strip().splitlines()
        if vers:
            v = vers[0].split()[1]
            hasUPX = tuple(map(int, v.split(".")))
            if is_win and is_py24 and hasUPX < (1, 92):
                logger.error('UPX is too old! Python 2.4 under Windows requires UPX 1.92+')
                hasUPX = 0
    except Exception, e:
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


def find_PYZ_dependencies(config):
    logger.debug("Computing PYZ dependencies")
    # We need to import `archive` from `PyInstaller` directory, but
    # not from package `PyInstaller`
    import PyInstaller.loader
    a = PyInstaller.depend.imptracker.ImportTracker([
        os.path.dirname(inspect.getsourcefile(PyInstaller.loader)),
        os.path.join(HOMEPATH, 'support')])

    a.analyze_r('archive')
    mod = a.modules['archive']
    toc = build.TOC([(mod.__name__, mod.__file__, 'PYMODULE')])
    for i, (nm, fnm, typ) in enumerate(toc):
        mod = a.modules[nm]
        tmp = []
        for importednm, isdelayed, isconditional, level in mod.imports:
            if not isconditional:
                realnms = a.analyze_one(importednm, nm)
                for realnm in realnms:
                    imported = a.modules[realnm]
                    if not isinstance(imported, PyInstaller.depend.modules.BuiltinModule):
                        tmp.append((imported.__name__, imported.__file__, imported.typ))
        toc.extend(tmp)
    toc.reverse()
    config['PYZ_dependencies'] = toc.data


def get_config(upx_dir, **kw):
    if is_darwin and compat.architecture() == '64bit':
        logger.warn('You are running 64-bit Python: created binaries will only'
            ' work on Mac OS X 10.6+.\nIf you need 10.4-10.5 compatibility,'
            ' run Python as a 32-bit binary with this command:\n\n'
            '    VERSIONER_PYTHON_PREFER_32_BIT=yes arch -i386 %s\n' % sys.executable)
        # wait several seconds for user to see this message
        time.sleep(4)

    # if not set by Make.py we can assume Windows
    config = {'useELFEXE': 1}
    test_Crypt(config)
    test_RsrcUpdate(config)
    test_UPX(config, upx_dir)
    find_PYZ_dependencies(config)
    return config
