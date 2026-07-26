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

import copy
import os
import pathlib
import subprocess
import sys

import pytest

from PyInstaller import compat
from PyInstaller.utils.tests import skipif

# PYI_PROCESS_LEVEL enum values from bootloader/src/pyi_main.h
PYI_PROCESS_LEVEL_UNKNOWN = -2
PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART = -1
PYI_PROCESS_LEVEL_PARENT = 0
PYI_PROCESS_LEVEL_MAIN = 1
PYI_PROCESS_LEVEL_SUBPROCESS = 2


# Check whether application's top level directory can be hijacked via manipulation of _PYI_ environment variables.
# See: https://github.com/pyinstaller/pyinstaller/security/advisories/GHSA-9fxf-4qw3-ghmr
@skipif(compat.is_aix or compat.is_openbsd or compat.is_hpux, reason="Mitigation is not available on this platform.")
@pytest.mark.parametrize(
    'parent_level',
    [
        PYI_PROCESS_LEVEL_UNKNOWN,
        PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART,
        PYI_PROCESS_LEVEL_PARENT,
        PYI_PROCESS_LEVEL_MAIN,
        PYI_PROCESS_LEVEL_SUBPROCESS,
    ],
    ids=[
        'UNKNOWN',
        'PARENT_NEEDS_RESTART',
        'PARENT',
        'MAIN',
        'SUBPROCESS',
    ],
)
def test_application_home_directory_hijack(pyi_builder, tmp_path, parent_level):
    mode = pyi_builder._mode  # Original mode

    # Create files with secrets
    SECRET_REAL = "REAL"
    SECRET_FAKE = "FAKE"

    real_secret_dir = tmp_path / 'real'
    real_secret_dir.mkdir()

    real_secret_file = real_secret_dir / 'secret.txt'
    real_secret_file.write_text(SECRET_REAL, encoding='utf-8')

    fake_secret_dir = tmp_path / 'fake'
    fake_secret_dir.mkdir()

    fake_secret_file = fake_secret_dir / 'secret.txt'
    fake_secret_file.write_text(SECRET_FAKE, encoding='utf-8')

    # Test script to use in both builds
    test_script = """
        import sys
        import os

        expected_secret = sys.argv[1]

        secret_file = os.path.join(sys._MEIPASS, 'secret.txt')
        with open(secret_file, 'r', encoding='utf-8') as fp:
            secret = fp.read().strip()

        print(f"Read secret: {secret}", file=sys.stderr)
        print(f"Expected secret: {expected_secret}", file=sys.stderr)

        if secret != expected_secret:
            print(f"Secret mismatch! {secret!r} vs {expected_secret!r}", file=sys.stderr)
            sys.exit(42)
    """

    # Build the test application
    pyi_builder.test_source(
        test_script,
        pyi_args=['--add-data', f'{str(real_secret_file)}:.'],
        app_name='app_real',
        app_args=[SECRET_REAL],
    )

    # Build the fake application - in onedir mode
    pyi_builder._mode = 'onedir'

    pyi_builder.test_source(
        test_script,
        pyi_args=['--add-data', f'{str(fake_secret_file)}:.'],
        app_name='app_fake',
        app_args=[SECRET_FAKE],
    )

    # The actual test - try to pass the fake application's contents
    # directory as top-level directory for the real test application.
    print("\nFinished build and sanity-check tests - preparing the actual test...", file=sys.stdout)
    print("\nFinished build and sanity-check tests - preparing the actual test...", file=sys.stderr)

    executables = pyi_builder._find_executables('app_real')
    assert len(executables) == 1
    executable = executables[0]
    print(f"Test application's executable: {executable}")

    executables = pyi_builder._find_executables('app_fake')
    assert len(executables) == 1
    fake_app_dir = pathlib.Path(executables[0]).parent / '_internal'
    print(f"Fake application's directory: {str(fake_app_dir)!r}")
    assert fake_app_dir.is_dir()

    # The cloak & dagger part...
    fake_env = copy.deepcopy(os.environ)
    # Prevent reset of _PYI_ environment variables
    archive_path = str(executable)
    if compat.is_win:
        # In an msys2 Windows environment, replace POSIX-style separators with Windows-style ones, which are used
        # within the bootloader...
        archive_path = archive_path.replace('/', '\\')
    fake_env['_PYI_ARCHIVE_FILE'] = archive_path
    # Try to trick process into running a specific codepath by manipulating its parent level.
    fake_env['_PYI_PARENT_PROCESS_LEVEL'] = str(parent_level)
    # Try to hijack the top-level application directory
    fake_env['_PYI_APPLICATION_HOME_DIR'] = str(fake_app_dir)

    print(f"Running executable: {executable}", file=sys.stdout)
    print(f"Running executable: {executable}", file=sys.stderr)
    p = subprocess.run([executable, SECRET_REAL], env=fake_env, capture_output=True, encoding='utf-8')

    print(f"Return code: {p.returncode}")

    if p.stdout:
        print(f"Captured stdout:\n----------------\n{p.stdout}\n----------------")
    else:
        print("Captured stdout: N/A")

    if p.stderr:
        print(f"Captured stderr:\n----------------\n{p.stderr}\n----------------")
    else:
        print("Captured stderr: N/A")

    # PYI_PROCESS_LEVEL_SUBPROCESS should be an invalid *parent* process level, regardless of mode.
    if parent_level == PYI_PROCESS_LEVEL_SUBPROCESS:
        assert p.returncode not in {0, 42}
        assert f"Invalid parent process level: {parent_level}" in p.stderr
        return

    # PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART should be invalid on Windows, macOS, and Cygwin, regardless of mode.
    non_posix = compat.is_win or compat.is_darwin or compat.is_cygwin
    if non_posix and parent_level == PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART:
        assert p.returncode not in {0, 42}
        assert f"Invalid parent process level: {parent_level}" in p.stderr
        return

    if mode == 'onedir':
        # In onedir build, the _PYI_APPLICATION_HOME_DIR environment variable should not be used at all - so the test
        # application should run normally, even if it is tricked into believing to be a sub-process of a onedir main
        # application process...
        assert p.returncode == 0
    else:
        # Onefile mode
        if parent_level == PYI_PROCESS_LEVEL_UNKNOWN:
            # This is same as _PYI_PARENT_PROCESS_LEVEL not being set at all; the process should run as parent process
            # of onefile application and set up new environment. Thus, the test application should run normally.
            assert p.returncode == 0
        elif parent_level == PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART:
            # This level is valid only in POSIX onefile builds with splash screen enabled. On non-POSIX systems, it
            # should exit with message about unrecognized level (handled by an earlier check). On POSIX systems, it
            # should similarly exit with message about unexpected level, since splash screen is not enabled on the
            # build; if it were enabled, the validation of directory name would fail instead.
            assert p.returncode not in {0, 42}
            assert "Security validation failure: unexpected process level!" in p.stderr or \
                "Security validation failure: unexpected name of application's home directory!" in p.stderr
        else:  # PYI_PROCESS_LEVEL_PARENT, PYI_PROCESS_LEVEL_MAIN
            # The process is supposed to be either These should fail the parent process verification in the bootloader.
            assert p.returncode not in {0, 42}
            assert "Security validation failure: parent process has different executable!" in p.stderr
