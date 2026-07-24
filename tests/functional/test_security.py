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

from PyInstaller import compat
from PyInstaller.utils.tests import skipif


# Check whether application's top level directory can be hijacked via manipulation of _PYI_ environment variables.
# See: https://github.com/pyinstaller/pyinstaller/security/advisories/GHSA-9fxf-4qw3-ghmr
@skipif(compat.is_aix or compat.is_openbsd or compat.is_hpux, reason="Mitigation is not available on this platform.")
def test_application_home_directory_hijack(pyi_builder, tmp_path):
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
    # Make the process believe it already has a parent. In onedir build, this would mean that the process is a worker
    # sub-process spawned from the main application process. In onefile build, this would mean that the process is the
    # main application process, and should use the ephemeral top-level application directory that was prepared by its
    # parent.
    fake_env['_PYI_PARENT_PROCESS_LEVEL'] = '0'
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

    if mode == 'onedir':
        # In onedir build, the _PYI_APPLICATION_HOME_DIR environment variable should not be used at all - so the test
        # application should run normally - even if it is tricked into believing to be a sub-process of a onedir main
        # application process...
        assert p.returncode == 0
    else:
        # Onefile mode - the test application should exit with non-zero return code. However, the error code should
        # also not be 42, which is used by the test program to indicate that it read the secret file in top-level
        # application directory and found it to be different from the expected one.
        assert p.returncode not in {0, 42}
        # Check for specific error message, which indicates that the process exited due to failed security validation
        # in the bootloader.
        assert "Security validation failure: parent process has different executable!" in p.stderr
