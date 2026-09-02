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
import shutil
import stat
import subprocess
import sys

import pytest

from PyInstaller import compat

# PYI_PROCESS_LEVEL enum values from bootloader/src/pyi_main.h
PYI_PROCESS_LEVEL_UNKNOWN = -2
PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART = -1
PYI_PROCESS_LEVEL_PARENT = 0
PYI_PROCESS_LEVEL_MAIN = 1
PYI_PROCESS_LEVEL_SUBPROCESS = 2

# ** Scenarios **
# Arbitrary directory passed as the application's top-level directory (i.e., does not have a _MEI prefix).
SCENARIO_ARBITRARY_DIR = 0
# Directory with _MEI prefix passed, but with PID part not corresponding to any process in the process ancestor tree.
SCENARIO_MEI_DIR_MISMATCHED_PID = 1
# Directory with _MEI prefix passed, and with PID part set to the PID of the current (pytest) process.
SCENARIO_MEI_DIR_MATCHED_PID = 2


def _ensure_long_path(path):
    if not compat.is_win and not compat.is_cygwin:
        return path

    # Bind GetLongPathNameW from kernel32.dll
    import ctypes
    import ctypes.wintypes

    kernel32 = ctypes.cdll.LoadLibrary("kernel32.dll")

    kernel32.GetLongPathNameW.restype = ctypes.wintypes.DWORD
    kernel32.GetLongPathNameW.argtypes = [
        ctypes.wintypes.LPCWSTR,  # LPCWSTR lpszShortPath
        ctypes.wintypes.LPWSTR,  # LPWSTR lpszLongPath
        ctypes.wintypes.DWORD,  # DWORD cchBuffer
    ]

    # Bind cygwin_conv_path from cygwin1.dll
    if compat.is_cygwin:
        cygwin = ctypes.cdll.LoadLibrary("cygwin1.dll")

        cygwin.cygwin_create_path.restype = ctypes.c_size_t
        cygwin.cygwin_create_path.argtypes = [
            ctypes.c_int32,  # cygwin_conv_path_t what
            ctypes.c_void_p,  # const void * from
            ctypes.c_void_p,  # void * to
            ctypes.c_size_t,  # size_t size
        ]

        CCP_POSIX_TO_WIN_W = 1
        CCP_WIN_W_TO_POSIX = 3

    path_len = 4096

    # Convert cygwin path to Windows path (long or short)
    if compat.is_cygwin:
        winpath_w = ctypes.create_unicode_buffer(path_len)
        ret = cygwin.cygwin_conv_path(
            CCP_POSIX_TO_WIN_W,
            ctypes.c_char_p(path.encode('utf-8')),
            winpath_w,
            path_len,
        )
        assert ret == 0, "Failed to convert POSIX path to Windows path!"
    else:
        winpath_w = ctypes.c_wchar_p(path)

    # Convert Windows path to long Windows path
    winpath_long_w = ctypes.create_unicode_buffer(path_len)
    ret = kernel32.GetLongPathNameW(winpath_w, winpath_long_w, path_len)

    # Convert long windows path to cygwin path
    if compat.is_cygwin:
        long_path = ctypes.create_string_buffer(path_len)
        ret = cygwin.cygwin_conv_path(
            CCP_WIN_W_TO_POSIX,
            winpath_long_w,
            long_path,
            path_len,
        )
        assert ret == 0, "Failed to convert POSIX path to Windows path!"
        long_path = long_path.value.decode('utf-8')
    else:
        long_path = winpath_long_w.value

    return long_path


def _enable_onefile_parent_verification(monkeypatch):
    import PyInstaller.building.build_main
    EXE = PyInstaller.building.build_main.EXE

    def MyEXE(*args, **kwargs):
        extra_options = [('pyi-enable-onefile-parent-verification', None, 'OPTION')]
        return EXE(*args, extra_options, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)


# Flag indicating that onefile parent-process verification is unavailable on the platform/system. With verification
# turned on (either due to privileged mode, or due to explicit opt-in), the program should raise an early error, which
# limits the scope of testing we can do.
verification_unavailable = (
    # OpenBSD does not have /proc filesystem available at all.
    compat.is_openbsd or
    # AIX has /proc filesystem available, but does not provide executable information.
    compat.is_aix or
    # On FreeBSD, /proc filesystem is not mounted by default
    (compat.is_freebsd and not os.path.isdir('/proc/curproc'))
)


# Check whether application's top level directory can be hijacked via manipulation of _PYI_ environment variables.
# See: https://github.com/pyinstaller/pyinstaller/security/advisories/GHSA-9fxf-4qw3-ghmr
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
@pytest.mark.parametrize(
    'scenario', [
        SCENARIO_ARBITRARY_DIR,
        SCENARIO_MEI_DIR_MISMATCHED_PID,
        SCENARIO_MEI_DIR_MATCHED_PID,
    ],
    ids=[
        'ArbitraryDir',
        'MeiDirMismatchedPid',
        'MeiDirMatchedPid',
    ]
)
@pytest.mark.parametrize('splash_enabled', [False, True], ids=['nosplash', 'splash'])
def test_application_home_directory_hijack(
    pyi_builder,
    tmp_path,
    script_dir,
    monkeypatch,
    splash_enabled,
    parent_level,
    scenario,
):
    # Enable onefile parent-process verification on the build
    _enable_onefile_parent_verification(monkeypatch)

    build_mode = pyi_builder._mode  # The original build mode (i.e., of the real test application)

    # Splash-screen enabled variant requires tkinter to build; but since we do not require splash screen to actually
    # work, we do not need to check if tkinter is fully-functional, only available.
    splash_args = []
    if splash_enabled:
        if compat.is_darwin:
            pytest.skip('splash screen is not supported on macOS')
        else:
            from PyInstaller.utils.hooks.tcl_tk import tcltk_info
            if not tcltk_info.available:
                pytest.skip('tkinter is not available')

        splash_image = script_dir.parent / 'data' / 'splash' / 'image.png'
        splash_args = ['--splash', str(splash_image)]

        # For this test, we need splash screen enabled in the build, but we are not interested in having it shown at
        # run-time. Therefore, explicitly suppress - primarily to avoid spurious errors on our Cygwin CI, where splash
        # screen tends to be flaky, but also to avoid unnecessarily running it on other platforms.
        monkeypatch.setenv("PYINSTALLER_SUPPRESS_SPLASH_SCREEN", "1")

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
    # If onefile parent-process verification is unavailable, we expect the program to fail here. The return code on
    # POSIX platforms (where verification might be unavailable) should be 255 (= (unsigned char)-1).
    expected_retcode = 255 if (build_mode == 'onefile' and verification_unavailable) else 0
    pyi_builder.test_source(
        test_script,
        pyi_args=['--add-data', f'{str(real_secret_file)}:.', *splash_args],
        app_name='app_real',
        app_args=[SECRET_REAL],
        retcode=expected_retcode,
    )

    # Build the fake application - in onedir mode
    pyi_builder._mode = 'onedir'

    pyi_builder.test_source(
        test_script,
        pyi_args=['--add-data', f'{str(fake_secret_file)}:.', *splash_args],
        app_name='app_fake',
        app_args=[SECRET_FAKE],
    )

    # The actual test - try to pass the fake application's contents
    # directory as top-level directory for the real test application.
    print("\nFinished build and sanity-check tests - preparing the actual test...", file=sys.stderr)

    executables = pyi_builder._find_executables('app_real')
    assert len(executables) == 1
    executable = executables[0]

    executables = pyi_builder._find_executables('app_fake')
    assert len(executables) == 1
    fake_app_dir = pathlib.Path(executables[0]).parent / '_internal'
    assert fake_app_dir.is_dir()

    # Scenario-specific adjustments to executable and/or application directory
    if scenario == SCENARIO_ARBITRARY_DIR:
        pass  # Pass the fake_app_dir and executable as-is
    elif scenario == SCENARIO_MEI_DIR_MISMATCHED_PID:
        # Copy the fake_app_dir into _MEI-formatted directory with PID part set to 0. The "random" part is also
        # set to 0, to pass the length check.
        mei_dir = tmp_path / f'_MEI{0:08x}000000'
        shutil.copytree(fake_app_dir, mei_dir, symlinks=True)
        fake_app_dir = mei_dir
    elif scenario == SCENARIO_MEI_DIR_MATCHED_PID:
        # Same as above, but with the process ID of the current (pytest) process. While technically a valid ancestor
        # process, it should still fail the executable check.
        mei_dir = tmp_path / f'_MEI{os.getpid():08x}000000'
        shutil.copytree(fake_app_dir, mei_dir, symlinks=True)
        fake_app_dir = mei_dir
    else:
        raise ValueError(f"Unsupported scenario: {scenario!r}")

    print(f"Test application's executable: {executable}", file=sys.stderr)
    print(f"Fake application's directory: {str(fake_app_dir)!r}", file=sys.stderr)

    # The cloak & dagger part...
    fake_env = copy.deepcopy(os.environ)
    # Prevent reset of _PYI_ environment variables
    archive_path = str(executable)
    if compat.is_win:
        # In an msys2 Windows environment, replace POSIX-style separators with Windows-style ones, which are used
        # within the bootloader...
        archive_path = archive_path.replace('/', '\\')
    # On Windows and Cygwin, ensure that we have long path instead of 8.3 short path. Bootloader determines archive
    # path from executable path, and that is resolved to long path.
    archive_path = _ensure_long_path(archive_path)
    if compat.is_cygwin and archive_path.lower().endswith('.exe'):
        archive_path = archive_path[:-4]  # Under Cygwin, bootloader resolves executable/archive without .exe suffix
    print(f"Setting _PYI_ARCHIVE_FILE to: {archive_path!r}", file=sys.stderr)
    fake_env['_PYI_ARCHIVE_FILE'] = archive_path
    # Try to trick process into running a specific codepath by manipulating its parent level.
    fake_env['_PYI_PARENT_PROCESS_LEVEL'] = str(parent_level)
    # Try to hijack the top-level application directory
    fake_env['_PYI_APPLICATION_HOME_DIR'] = str(fake_app_dir)

    print(f"Running executable: {executable}", file=sys.stderr)
    p = subprocess.run([executable, SECRET_REAL], env=fake_env, capture_output=True, encoding='utf-8')

    print(f"Return code: {p.returncode}", file=sys.stderr)

    if p.stdout:
        print(f"Captured stdout:\n----------------\n{p.stdout}\n----------------", file=sys.stderr)
    else:
        print("Captured stdout: N/A", file=sys.stderr)

    if p.stderr:
        print(f"Captured stderr:\n----------------\n{p.stderr}\n----------------", file=sys.stderr)
    else:
        print("Captured stderr: N/A", file=sys.stderr)

    # PYI_PROCESS_LEVEL_SUBPROCESS should be an invalid *parent* process level, regardless of mode.
    if parent_level == PYI_PROCESS_LEVEL_SUBPROCESS:
        assert p.returncode not in {0, 42}
        assert f"Invalid parent process level: {parent_level}" in p.stderr
        return

    # PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART should be invalid on Windows, macOS, and Cygwin, regardless of build mode
    # and regardless of whether splash screen is enabled in the build or not. On other platforms, it is valid for onedir
    # mode, and for onefile mode with splash screen enabled.
    if parent_level == PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART:
        if compat.is_win or compat.is_darwin or compat.is_cygwin:
            assert p.returncode not in {0, 42}
            assert f"Invalid parent process level: {parent_level}" in p.stderr
            return
        elif build_mode == 'onefile' and not splash_enabled:
            assert p.returncode not in {0, 42}
            assert "Security validation failure: unexpected process level!" in p.stderr
            return

    # *** Onedir mode ***
    if build_mode == 'onedir':
        # In a onedir build, the _PYI_APPLICATION_HOME_DIR environment variable should not be used at all - so the test
        # application should run normally, even if it is tricked into believing to be a sub-process of a onedir main
        # application process...
        assert p.returncode == 0
        return

    # *** Onefile mode ***
    ERR_HOME_DIRECTORY_NAME = \
        "Security validation failure: unexpected name of application's home directory!"
    ERR_HOME_DIRECTORY_PID = \
        "Security validation failure: unexpected PID found in the name of application's home directory!"
    ERR_PARENT_DIFFERENT_EXECUTABLE = \
        "Security validation failure: invalid originating onefile parent process (different executable)!"
    ERR_PARENT_DIFFERENT_PID = \
        "Security validation failure: invalid originating onefile parent process (different PID)!"
    ERR_PARENT_PID_NOT_FOUND = \
        "Security validation failure: invalid originating onefile parent process (PID not found)!"

    # On unsupported platforms, the program should raise an early error.
    if verification_unavailable:
        assert p.returncode not in {0, 42}
        if compat.is_freebsd:
            # FreeBSD without /proc mounted
            ERR_UNSUPPORTED_SYSTEM = (
                "Security validation failure: setuid-enabled executables are not supported on this system "
                "(missing /proc)!"
            )
            assert ERR_UNSUPPORTED_SYSTEM in p.stderr
        else:
            # AIX, OpenBSD
            ERR_UNSUPPORTED_PLATFORM = \
                "Security validation failure: setuid-enabled executables are not supported on this platform!"
            assert ERR_UNSUPPORTED_PLATFORM in p.stderr
        return

    if parent_level == PYI_PROCESS_LEVEL_UNKNOWN:
        # This is same as _PYI_PARENT_PROCESS_LEVEL not being set at all; the process should run as parent process
        # of onefile application and set up new environment. Thus, the test application should run normally.
        # (Except in the setuid-executable scenario with mitigation being unavailable, which should already be
        # handled by earlier check.)
        assert p.returncode == 0
    elif parent_level == PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART:
        # This level is valid only in POSIX onefile builds with splash screen enabled. Since the process retains
        # its process ID across restart, it can always detect mismatch in the home directory name.
        assert p.returncode not in {0, 42}
        if scenario == SCENARIO_ARBITRARY_DIR:
            assert ERR_HOME_DIRECTORY_NAME in p.stderr
        else:
            assert ERR_HOME_DIRECTORY_PID in p.stderr
    else:  # PYI_PROCESS_LEVEL_PARENT, PYI_PROCESS_LEVEL_MAIN
        # The process is supposed to be either main application process, or worker sub-process spawned via
        # `sys.executable`. The arbitrarily-named application directory should fail the name check. The
        # _MEI-formatted application directory should pass the name check, but should fail the parent-process
        # validation.
        #
        # On platforms where procfs-based look-up of parent executable is not supported (AIX, OpenBSD) or the
        # relevant entry under /proc/<ppid> is inaccessible (e.g., FreeBSD without /proc mounted, or any other
        # supported POSIX platform where local security policy blocks access to /proc/<ppid> directory for other
        # processes), we cannot validate the parent process. In these cases, we expect the validation of
        # arbitrary home directory name to fail, the faked home directory with _MEI prefix to slip through,
        # and executable with setuid bit set to block the execution (already handled by preceding if-block).
        if scenario == SCENARIO_ARBITRARY_DIR:
            assert p.returncode not in {0, 42}
            assert ERR_HOME_DIRECTORY_NAME in p.stderr
        elif scenario == SCENARIO_MEI_DIR_MISMATCHED_PID:
            # The PID part of _MEI directory in this scenario is set to 0.
            #
            # When running as main application process level (i.e., the spoofed parent process level is
            # PYI_PROCESS_LEVEL_PARENT), the declared PID=0 differs from that of immediate parent, and fails
            # the validation.
            #
            # When running as spawned worker sub-process (i.e., the spoofed parent process level is
            # PYI_PROCESS_LEVEL_MAIN), the declared PID=0 cannot be found among ancestor processes, and fails
            # the validation.
            assert p.returncode not in {0, 42}
            if parent_level == PYI_PROCESS_LEVEL_PARENT:
                assert ERR_PARENT_DIFFERENT_PID in p.stderr
            else:
                assert ERR_PARENT_PID_NOT_FOUND in p.stderr
        elif scenario == SCENARIO_MEI_DIR_MATCHED_PID:
            # The PID part of _MEI directory in this scenario is set to the PID of current (= pytest) process.
            #
            # When running as main application process level (i.e., the spoofed parent process level is
            # PYI_PROCESS_LEVEL_PARENT), the declared PID matches that of immediate parent, and passes
            # validation; therefore, it fails in subsequent executable validation.
            #
            # When running as spawned worker sub-process (i.e., the spoofed parent process level is
            # PYI_PROCESS_LEVEL_MAIN), the declared PID matches that of immediate parent; this fails the
            # validation, because in this case we expect the originating onefile parent process to be at least
            # a grand-parent or a further ancestor.
            assert p.returncode not in {0, 42}
            if parent_level == PYI_PROCESS_LEVEL_PARENT:
                assert ERR_PARENT_DIFFERENT_EXECUTABLE in p.stderr
            else:
                assert ERR_PARENT_DIFFERENT_PID in p.stderr
        else:
            raise ValueError(f"Unsupported scenario: {scenario!r}")


# Test that in onefile mode, parent-process security validation is automatically enabled for executable that has setuid
# bit set. Test that in onedir mode, the permissions on application's contents directory are verified.
@pytest.mark.skipif(compat.is_win, reason="applicable only to POSIX platforms.")
def test_security_validation_with_setuid_executable(pyi_builder, tmp_path, monkeypatch):
    # Do NOT enable onefile parent-process verification on the build!

    # Basic test application
    pyi_builder.test_source("""
        import sys
        print("Hello world", file=sys.stderr)
    """)

    print("\nFinished build and sanity-check tests - preparing the actual test...", file=sys.stderr)

    executables = pyi_builder._find_executables('test_source')
    assert len(executables) == 1
    executable = executables[0]

    # Set setuid bit on the executable. The file is owned by current user, so this is not a "real" setuid-root scenario.
    # But since the bootloader checks the setuid bit, it should suffice for the purposes of the test.
    st_mode = os.lstat(executable).st_mode
    os.chmod(executable, st_mode | stat.S_ISUID)

    print(f"Running executable with setuid bit set: {executable}", file=sys.stderr)
    p = subprocess.run([executable], capture_output=True, encoding='utf-8')

    print(f"Return code: {p.returncode}", file=sys.stderr)

    if p.stdout:
        print(f"Captured stdout:\n----------------\n{p.stdout}\n----------------", file=sys.stderr)
    else:
        print("Captured stdout: N/A", file=sys.stderr)

    if p.stderr:
        print(f"Captured stderr:\n----------------\n{p.stderr}\n----------------", file=sys.stderr)
    else:
        print("Captured stderr: N/A", file=sys.stderr)

    # Ensure that setuid bit was detected
    assert "SECURITY: executable has setuid bit set" in p.stderr

    MSG_VERIFICATION = "SECURITY: setuid bit is set - verifying owner/permissions of application's home directory..."

    if pyi_builder._mode == 'onefile':
        # Onefile mode
        if verification_unavailable:
            # If onefile parent-process verification is unavailable, the setuid-enabled executable should raise an early
            # error.
            assert p.returncode != 0

            if compat.is_freebsd:
                ERR_MSG = (
                    "Security validation failure: setuid-enabled executables are not supported on this system "
                    "(missing /proc)!"
                )
            else:
                ERR_MSG = "Security validation failure: setuid-enabled executables are not supported on this platform!"
            assert ERR_MSG in p.stderr
        else:
            assert p.returncode == 0

            # Ensure that owner/permissions on application's home directory were validated
            assert MSG_VERIFICATION in p.stderr

            # Ensure that onefile-parent process validation was auto-enabled, and performed.
            assert "SECURITY: verifying onefile parent process due to executable running in privileged mode..." \
                in p.stderr
            assert "SECURITY: verifying process ID of originating onefile parent process" in p.stderr
            assert "SECURITY: verifying executable of originating onefile parent process" in p.stderr
    else:
        # Onedir mode: check that program failed due to incorrect permissions on application's contents directory. The
        # actual permissions may vary between platforms (for example, 0755 on linux, 0775 on Cygwin), so skip that part
        # of the message.
        assert p.returncode != 0

        assert MSG_VERIFICATION in p.stderr
        assert "Security validation failure: application's home directory has invalid permissions (" in p.stderr

        # Adjust permissions on contents directory, and try again.
        contents_dir = pathlib.Path(executable).with_name('_internal')
        os.chmod(contents_dir, stat.S_IRWXU)  # 0700

        print("Running executable after adjusting permissions on contents directory", file=sys.stderr)
        p = subprocess.run([executable], capture_output=True, encoding='utf-8')

        print(f"Return code: {p.returncode}", file=sys.stderr)

        if p.stdout:
            print(f"Captured stdout:\n----------------\n{p.stdout}\n----------------", file=sys.stderr)
        else:
            print("Captured stdout: N/A", file=sys.stderr)

        if p.stderr:
            print(f"Captured stderr:\n----------------\n{p.stderr}\n----------------", file=sys.stderr)
        else:
            print("Captured stderr: N/A", file=sys.stderr)

        # The program should succeed now
        assert p.returncode == 0
        assert "SECURITY: executable has setuid bit set" in p.stderr
        assert MSG_VERIFICATION in p.stderr


# Test that parent-process security validation works correctly in case of symlinked executables (i.e., the executable
# itself being symlinked, or one of its parent directories being symlinked). See #9508.
def test_security_validation_with_symlinked_executable(pyi_builder, tmp_path, monkeypatch):
    # Skip if onefile parent-process verification is unavailable
    if pyi_builder._mode == 'onefile' and verification_unavailable:
        pytest.skip(reason='onefile parent-process verification is unavailable on this platform/system.')

    # Enable onefile parent-process verification on the build
    _enable_onefile_parent_verification(monkeypatch)

    # Ensure that symbolic links can be created
    try:
        test_dir = tmp_path / 'sanity-check' / 'test-dir'
        test_dir.mkdir(parents=True)
        test_file = tmp_path / 'sanity-check' / 'test-file.txt'
        test_file.write_text('Test', encoding='utf-8')

        test_dir_symlink = tmp_path / 'sanity-check' / 'test-dir-symlink'
        test_file_symlink = tmp_path / 'sanity-check' / 'test-file-symlink.txt'

        os.symlink(test_file, test_file_symlink)
        os.symlink(test_dir, test_dir_symlink, target_is_directory=True)
    except OSError:
        if compat.is_win:
            pytest.skip("OS does not support creation of symbolic links.")
        else:
            raise

    # Basic test application
    pyi_builder.test_source("""
        import sys
        print("Hello world", file=sys.stderr)
    """)

    print("\nFinished build and sanity-check tests - preparing the actual test...", file=sys.stderr)

    executables = pyi_builder._find_executables('test_source')
    assert len(executables) == 1
    executable = executables[0]
    print(f"Test application's executable: {executable}", file=sys.stderr)

    # Symlinked executable
    symlinked_exe = tmp_path / ('symlinked_executable.exe' if compat.is_win else 'symlinked_executable')
    os.symlink(executable, symlinked_exe)

    print(f"Running symlinked executable: {symlinked_exe}", file=sys.stderr)
    p = subprocess.run([symlinked_exe], check=True, capture_output=True, encoding='utf-8')

    print(f"Return code: {p.returncode}", file=sys.stderr)

    if p.stdout:
        print(f"Captured stdout:\n----------------\n{p.stdout}\n----------------", file=sys.stderr)
    else:
        print("Captured stdout: N/A", file=sys.stderr)

    if p.stderr:
        print(f"Captured stderr:\n----------------\n{p.stderr}\n----------------", file=sys.stderr)
    else:
        print("Captured stderr: N/A", file=sys.stderr)

    # Ensure that onefile-parent process validation was enabled, and performed.
    if pyi_builder._mode == 'onefile':
        assert "SECURITY: verifying onefile parent process due to explicit opt-in..." in p.stderr
        assert "SECURITY: verifying process ID of originating onefile parent process" in p.stderr
        assert "SECURITY: verifying executable of originating onefile parent process" in p.stderr

    # Symlinked dist directory
    symlinked_dist = tmp_path / 'symlinked-dist'
    os.symlink(tmp_path / 'dist', symlinked_dist)
    symlinked_dist_exe = symlinked_dist / pathlib.Path(executable).relative_to(tmp_path / 'dist')

    print(f"Running executable in symlinked dist directory: {symlinked_dist_exe}", file=sys.stderr)
    p = subprocess.run([symlinked_dist_exe], check=True, capture_output=True, encoding='utf-8')

    print(f"Return code: {p.returncode}", file=sys.stderr)

    if p.stdout:
        print(f"Captured stdout:\n----------------\n{p.stdout}\n----------------", file=sys.stderr)
    else:
        print("Captured stdout: N/A", file=sys.stderr)

    if p.stderr:
        print(f"Captured stderr:\n----------------\n{p.stderr}\n----------------", file=sys.stderr)
    else:
        print("Captured stderr: N/A", file=sys.stderr)

    # Ensure that onefile-parent process validation was enabled, and performed.
    if pyi_builder._mode == 'onefile':
        assert "SECURITY: verifying onefile parent process due to explicit opt-in..." in p.stderr
        assert "SECURITY: verifying process ID of originating onefile parent process" in p.stderr
        assert "SECURITY: verifying executable of originating onefile parent process" in p.stderr


# Test that parent-process security validation works correctly with nested subprocsses.
def test_security_validation_with_subprocesses(pyi_builder, tmp_path, monkeypatch, capfd):
    # Skip if onefile parent-process verification is unavailable
    if pyi_builder._mode == 'onefile' and verification_unavailable:
        pytest.skip(reason='onefile parent-process verification is unavailable on this platform/system.')

    # Enable onefile parent-process verification on the build
    _enable_onefile_parent_verification(monkeypatch)

    # Test program
    pyi_builder.test_source(
        """
        import sys
        import os
        import subprocess

        if len(sys.argv) == 2:
            print("Running as main process...", file=sys.stderr)
            print("Starting subprocess...", file=sys.stderr)
            subprocess.run([sys.executable], check=True)
        else:
            print("Running as subprocess", file=sys.stderr)

        print("Done!")
        """,
        app_args=['main']
    )

    # Ensure that onefile-parent process validation was enabled, and performed.
    #
    # NOTE: we need to use capfd instead of capsys to capture output from the test program subprocess(es).
    # Unfortunately this means that in the case of a test program failure, we do not get any captured output from it...
    if pyi_builder._mode == 'onefile':
        _, err = capfd.readouterr()

        assert "SECURITY: verifying onefile parent process due to explicit opt-in..." in err
        assert "SECURITY: verifying process ID of originating onefile parent process" in err
        assert "SECURITY: verifying executable of originating onefile parent process" in err


# Test that parent-process security validation works correctly in case of intermixed processes, i.e., the application
# process spawning another program, which then spawns another instance of application (subprocess). See #9512 and #9513.
def test_security_validation_with_intermixed_subprocesses(pyi_builder, tmp_path, capfd, monkeypatch):
    # Skip if onefile parent-process verification is unavailable
    if pyi_builder._mode == 'onefile' and verification_unavailable:
        pytest.skip(reason='onefile parent-process verification is unavailable on this platform/system.')

    # Enable onefile parent-process verification on the build
    _enable_onefile_parent_verification(monkeypatch)

    # Wrapper script
    wrapper_script = '\n'.join([
        "import sys",
        "import subprocess",
        "print('Wrapper script: launching executable...', file=sys.stderr)",
        "subprocess.run(sys.argv[1:3], check=True)",
        "print('Wrapper script: done!', file=sys.stderr)",
    ])
    script_file = tmp_path / "wrapper_script.py"
    script_file.write_text(wrapper_script, encoding='utf-8')

    # Test program
    pyi_builder.test_source(
        """
        import sys
        import os
        import subprocess

        if len(sys.argv) == 3:
            output_dir = sys.argv[1]
            python_executable = sys.argv[2]
            mode = 'main'
        elif len(sys.argv) == 2:
            output_dir = sys.argv[1]
            mode = 'nested'
        else:
            raise ValueError("Invalid number of arguments")

        # Write path to top-level application directory to a file
        print(f"Application top-level directory: {sys._MEIPASS!r}", file=sys.stderr)
        output_file = os.path.join(output_dir, mode + '.txt')
        with open(output_file, 'w', encoding='utf-8') as fp:
            print(sys._MEIPASS, file=fp)

        # In main mode, spawn python process to run the wrapper script (which will run the executable again)
        if mode == 'main':
            print("Running wrapper script...", file=sys.stderr)
            script_file = os.path.join(output_dir, 'wrapper_script.py')
            subprocess.run([python_executable, script_file, sys.executable, output_dir], check=True)
        """,
        app_args=[str(tmp_path), str(compat.python_executable)]
    )

    # Ensure that onefile-parent process validation was enabled, and performed.
    if pyi_builder._mode == 'onefile':
        _, err = capfd.readouterr()

        assert "SECURITY: verifying onefile parent process due to explicit opt-in..." in err
        assert "SECURITY: verifying process ID of originating onefile parent process" in err
        assert "SECURITY: verifying executable of originating onefile parent process" in err

    # Check that both processes used the same top-level application directory
    output_file_main = tmp_path / 'main.txt'
    application_dir_main = output_file_main.read_text(encoding='utf-8').strip()
    print(f"Top-level application directory (main): {application_dir_main!r}", file=sys.stderr)

    output_file_nested = tmp_path / 'nested.txt'
    application_dir_nested = output_file_nested.read_text(encoding='utf-8').strip()
    print(f"Top-level application directory (nested): {application_dir_nested!r}", file=sys.stderr)

    assert application_dir_main == application_dir_nested
