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

import contextlib
import copy
import glob
import logging
import os
import platform
import re
import shutil
import subprocess
import sys

# Set a handler for the root-logger to inhibit 'basicConfig()' (called in PyInstaller.log) is setting up a stream
# handler writing to stderr. This avoids log messages to be written (and captured) twice: once on stderr and
# once by pytests's caplog.
logging.getLogger().addHandler(logging.NullHandler())

# psutil is used for process tree clean-up on time-out when running the test frozen application. If unavailable
# (for example, on cygwin), we fall back to trying to terminate only the main application process.
try:
    import psutil  # noqa: E402
except ModuleNotFoundError:
    psutil = None

import py  # noqa: E402
import pytest  # noqa: E402

# Expand sys.path with PyInstaller source.
_ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(_ROOT_DIR)

from PyInstaller import __main__ as pyi_main  # noqa: E402
from PyInstaller import configure  # noqa: E402
from PyInstaller.compat import architecture, is_darwin, is_win  # noqa: E402
from PyInstaller.depend.analysis import initialize_modgraph  # noqa: E402
from PyInstaller.archive.readers import pkg_archive_contents  # noqa: E402
from PyInstaller.utils.tests import gen_sourcefile  # noqa: E402
from PyInstaller.utils.win32 import winutils  # noqa: E402

# Timeout for running the executable. If executable does not exit in this time, it is interpreted as a test failure.
_EXE_TIMEOUT = 3 * 60  # In sec.
# All currently supported platforms
SUPPORTED_OSES = {"darwin", "linux", "win32"}
# Have pyi_builder fixure clean-up the temporary directories of successful tests. Controlled by environment variable.
_PYI_BUILDER_CLEANUP = os.environ.get("PYI_BUILDER_CLEANUP", "1") == "1"

# Fixtures
# --------


@pytest.fixture
def SPEC_DIR(request):
    """
    Return the directory where the test spec-files reside.
    """
    return py.path.local(_get_spec_dir(request))


@pytest.fixture
def SCRIPT_DIR(request):
    """
    Return the directory where the test scripts reside.
    """
    return py.path.local(_get_script_dir(request))


def pytest_runtest_setup(item):
    """
    Markers to skip tests based on the current platform.
    https://pytest.org/en/stable/example/markers.html#marking-platform-specific-tests-with-pytest

    Available markers: see setup.cfg [tool:pytest] markers
        - @pytest.mark.darwin (macOS)
        - @pytest.mark.linux (GNU/Linux)
        - @pytest.mark.win32 (Windows)
    """
    supported_platforms = SUPPORTED_OSES.intersection(mark.name for mark in item.iter_markers())
    plat = sys.platform
    if supported_platforms and plat not in supported_platforms:
        pytest.skip(f"does not run on {plat}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Execute all other hooks to obtain the report object.
    outcome = yield
    rep = outcome.get_result()

    # Set a report attribute for each phase of a call, which can be "setup", "call", "teardown".
    setattr(item, f"rep_{rep.when}", rep)


# Return the base directory which contains the current test module.
def _get_base_dir(request):
    return os.path.dirname(os.path.abspath(request.fspath.strpath))


# Directory with Python scripts for functional tests.
def _get_script_dir(request):
    return os.path.join(_get_base_dir(request), 'scripts')


# Directory with testing modules used in some tests.
def _get_modules_dir(request):
    return os.path.join(_get_base_dir(request), 'modules')


# Directory with .toc log files.
def _get_logs_dir(request):
    return os.path.join(_get_base_dir(request), 'logs')


# Return the directory where data for tests is located.
def _get_data_dir(request):
    return os.path.join(_get_base_dir(request), 'data')


# Directory with .spec files used in some tests.
def _get_spec_dir(request):
    return os.path.join(_get_base_dir(request), 'specs')


@pytest.fixture
def script_dir(request):
    return py.path.local(_get_script_dir(request))


# A helper function to copy from data/dir to tmpdir/data.
def _data_dir_copy(
    # The pytest request object.
    request,
    # The name of the subdirectory located in data/name to copy.
    subdir_name,
    # The tmpdir object for this test. See: https://pytest.org/latest/tmpdir.html.
    tmpdir
):

    # Form the source and tmp paths.
    source_data_dir = py.path.local(_get_data_dir(request)).join(subdir_name)
    tmp_data_dir = tmpdir.join('data', subdir_name)
    # Copy the data.
    shutil.copytree(source_data_dir.strpath, tmp_data_dir.strpath)
    # Return the temporary data directory, so that the copied data can now be used.
    return tmp_data_dir


# Define a fixure for the DataDir object.
@pytest.fixture
def data_dir(
    # The request object for this test. See
    # https://pytest.org/latest/builtin.html#_pytest.python.FixtureRequest
    # and
    # https://pytest.org/latest/fixture.html#fixtures-can-introspect-the-requesting-test-context.
    request,
    # The tmpdir object for this test. See https://pytest.org/latest/tmpdir.html.
    tmpdir
):

    # Strip the leading 'test_' from the test's name.
    name = request.function.__name__[5:]
    # Copy to tmpdir and return the path.
    return _data_dir_copy(request, name, tmpdir)


class AppBuilder:
    def __init__(self, tmpdir, request, bundle_mode):
        self._tmpdir = tmpdir
        self._request = request
        self._mode = bundle_mode
        self._specdir = str(tmpdir)
        self._distdir = str(tmpdir / 'dist')
        self._builddir = str(tmpdir / 'build')
        self._is_spec = False

    def test_spec(self, specfile, *args, **kwargs):
        """
        Test a Python script that is referenced in the supplied .spec file.
        """
        __tracebackhide__ = True
        specfile = os.path.join(_get_spec_dir(self._request), specfile)
        # 'test_script' should handle .spec properly as script.
        self._is_spec = True
        return self.test_script(specfile, *args, **kwargs)

    def test_source(self, source, *args, **kwargs):
        """
        Test a Python script given as source code.

        The source will be written into a file named like the test-function. This file will then be passed to
        `test_script`. If you need other related file, e.g., as `.toc`-file for testing the content, put it at at the
        normal place. Just mind to take the basnename from the test-function's name.

        :param script: Source code to create executable from. This will be saved into a temporary file which is then
                       passed on to `test_script`.

        :param test_id: Test-id for parametrized tests. If given, it will be appended to the script filename, separated
                        by two underscores.

        All other arguments are passed straight on to `test_script`.

        Ensure that the caller of `test_source` is in a UTF-8 encoded file with the correct '# -*- coding: utf-8 -*-'
        marker.

        """
        __tracebackhide__ = True
        # For parametrized test append the test-id.
        scriptfile = gen_sourcefile(self._tmpdir, source, kwargs.setdefault('test_id'))
        del kwargs['test_id']
        return self.test_script(str(scriptfile), *args, **kwargs)

    def _display_message(self, step_name, message):
        # Print the given message to both stderr and stdout, and it with APP-BUILDER to make it clear where it
        # originates from.
        print(f'[APP-BUILDER:{step_name}] {message}', file=sys.stdout)
        print(f'[APP-BUILDER:{step_name}] {message}', file=sys.stderr)

    def test_script(
        self, script, pyi_args=None, app_name=None, app_args=None, runtime=None, run_from_path=False, **kwargs
    ):
        """
        Main method to wrap all phases of testing a Python script.

        :param script: Name of script to create executable from.
        :param pyi_args: Additional arguments to pass to PyInstaller when creating executable.
        :param app_name: Name of the executable. This is equivalent to argument --name=APPNAME.
        :param app_args: Additional arguments to pass to
        :param runtime: Time in seconds how long to keep executable running.
        :param toc_log: List of modules that are expected to be bundled with the executable.
        """
        __tracebackhide__ = True

        # Skip interactive tests (the ones with `runtime` set) if `psutil` is unavailable, as we need it to properly
        # clean up the process tree.
        if runtime and psutil is None:
            pytest.skip('Interactive tests require psutil for proper cleanup.')

        if pyi_args is None:
            pyi_args = []
        if app_args is None:
            app_args = []

        if app_name:
            if not self._is_spec:
                pyi_args.extend(['--name', app_name])
        else:
            # Derive name from script name.
            app_name = os.path.splitext(os.path.basename(script))[0]

        # Relative path means that a script from _script_dir is referenced.
        if not os.path.isabs(script):
            script = os.path.join(_get_script_dir(self._request), script)
        self.script = script
        assert os.path.exists(self.script), f'Script {script} not found.'

        self._display_message('TEST-SCRIPT', 'Starting build...')
        if not self._test_building(args=pyi_args):
            pytest.fail(f'Building of {script} failed.')

        self._display_message('TEST-SCRIPT', 'Build finished, now running executable...')
        self._test_executables(app_name, args=app_args, runtime=runtime, run_from_path=run_from_path, **kwargs)
        self._display_message('TEST-SCRIPT', 'Running executable finished.')

    def _test_executables(self, name, args, runtime, run_from_path, **kwargs):
        """
        Run created executable to make sure it works.

        Multipackage-tests generate more than one exe-file and all of them have to be run.

        :param args: CLI options to pass to the created executable.
        :param runtime: Time in seconds how long to keep the executable running.

        :return: Exit code of the executable.
        """
        __tracebackhide__ = True
        exes = self._find_executables(name)
        # Empty list means that PyInstaller probably failed to create any executable.
        assert exes != [], 'No executable file was found.'
        for exe in exes:
            # Try to find .toc log file. .toc log file has the same basename as exe file.
            toc_log = os.path.join(_get_logs_dir(self._request), os.path.splitext(os.path.basename(exe))[0] + '.toc')
            if os.path.exists(toc_log):
                if not self._examine_executable(exe, toc_log):
                    pytest.fail(f'Matching .toc of {exe} failed.')
            retcode = self._run_executable(exe, args, run_from_path, runtime)
            if retcode != kwargs.get('retcode', 0):
                pytest.fail(f'Running exe {exe} failed with return-code {retcode}.')

    def _find_executables(self, name):
        """
        Search for all executables generated by the testcase.

        If the test-case is called e.g. 'test_multipackage1', this is searching for each of 'test_multipackage1.exe'
        and 'multipackage1_?.exe' in both one-file- and one-dir-mode.

        :param name: Name of the executable to look for.

        :return: List of executables
        """
        exes = []
        onedir_pt = os.path.join(self._distdir, name, name)
        onefile_pt = os.path.join(self._distdir, name)
        patterns = [
            onedir_pt,
            onefile_pt,
            # Multipackage one-dir
            onedir_pt + '_?',
            # Multipackage one-file
            onefile_pt + '_?'
        ]
        # For Windows append .exe extension to patterns.
        if is_win:
            patterns = [pt + '.exe' for pt in patterns]
        # For Mac OS append pattern for .app bundles.
        if is_darwin:
            # e.g:  ./dist/name.app/Contents/MacOS/name
            pt = os.path.join(self._distdir, name + '.app', 'Contents', 'MacOS', name)
            patterns.append(pt)
        # Apply file patterns.
        for pattern in patterns:
            for prog in glob.glob(pattern):
                if os.path.isfile(prog):
                    exes.append(prog)
        return exes

    def _run_executable(self, prog, args, run_from_path, runtime):
        """
        Run executable created by PyInstaller.

        :param args: CLI options to pass to the created executable.
        """
        # Run the test in a clean environment to make sure they're really self-contained.
        prog_env = copy.deepcopy(os.environ)
        prog_env['PATH'] = ''
        del prog_env['PATH']
        # For Windows we need to keep minimal PATH for successful running of some tests.
        if is_win:
            # Minimum Windows PATH is in most cases:   C:\Windows\system32;C:\Windows
            prog_env['PATH'] = os.pathsep.join(winutils.get_system_path())
        # On macOS, we similarly set up minimal PATH with system directories, in case utilities from there are used by
        # tested python code (for example, matplotlib >= 3.9.0 uses `system_profiler` that is found in /usr/sbin).
        if is_darwin:
            # The following paths are registered when application is launched via Finder, and are a subset of what is
            # typically available in the shell.
            prog_env['PATH'] = os.pathsep.join(['/usr/bin', '/bin', '/usr/sbin', '/sbin'])

        exe_path = prog
        if run_from_path:
            # Run executable in the temp directory. Add the directory containing the executable to $PATH. Basically,
            # pretend we are a shell executing the program from $PATH.
            prog_cwd = str(self._tmpdir)
            prog_name = os.path.basename(prog)
            prog_env['PATH'] = os.pathsep.join([prog_env.get('PATH', ''), os.path.dirname(prog)])

        else:
            # Run executable in the directory where it is.
            prog_cwd = os.path.dirname(prog)
            # The executable will be called with argv[0] as relative not absolute path.
            prog_name = os.path.join(os.curdir, os.path.basename(prog))

        args = [prog_name] + args
        # Using sys.stdout/sys.stderr for subprocess fixes printing messages in Windows command prompt. Py.test is then
        # able to collect stdout/sterr messages and display them if a test fails.
        return self._run_executable_(args, exe_path, prog_env, prog_cwd, runtime)

    def _run_executable_(self, args, exe_path, prog_env, prog_cwd, runtime):
        # Use psutil.Popen, if available; otherwise, fall back to subprocess.Popen
        popen_implementation = subprocess.Popen if psutil is None else psutil.Popen

        # Run the executable
        self._display_message('RUN-EXE', f'Running {exe_path!r}, args: {args!r}')
        process = popen_implementation(
            args, executable=exe_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=prog_env, cwd=prog_cwd
        )
        self._display_message('RUN-EXE', f'Process ID: {process.pid}')

        # Wait for the process to finish. If no run-time (= timeout) is specified, we expect the process to exit on
        # its own, and use global _EXE_TIMEOUT. If run-time is specified, we expect the application to be running
        # for at least the specified amount of time, which is useful in "interactive" test applications that are not
        # expected exit on their own.
        stdout = stderr = None
        try:
            timeout = runtime if runtime else _EXE_TIMEOUT
            stdout, stderr = process.communicate(timeout=timeout)
            retcode = process.returncode
            self._display_message('RUN-EXE', f'Process exited on its own with return code {retcode}.')
        except (subprocess.TimeoutExpired) if psutil is None else (psutil.TimeoutExpired, subprocess.TimeoutExpired):
            if runtime:
                # When 'runtime' is set, the expired timeout is a good sign that the executable was running successfully
                # for the specified time.
                self._display_message('RUN-EXE', f'Process reached expected run-time of {runtime} seconds.')
                retcode = 0
            else:
                # Executable is still running and it is not interactive. Clean up the process tree, and fail the test.
                self._display_message('RUN-EXE', f'Timeout while running executable (timeout: {timeout} seconds)!')
                retcode = 1

            if psutil is None:
                # We are using subprocess.Popen(). Without psutil, we have no access to process tree; this poses a
                # problem for onefile builds, where we would need to first kill the child (main application) process,
                # and let the onefile parent perform its cleanup. As a best-effort approach, we can first call
                # process.terminate(); on POSIX systems, this sends SIGTERM to the parent process, and in most
                # situations, the bootloader will forward it to the child process. Then wait 5 seconds, and call
                # process.kill() if necessary. On Windows, however, both process.terminate() and process.kill() do
                # the same. Therefore, we should avoid running "interactive" tests with expected run-time if we do
                # not have psutil available.
                try:
                    self._display_message('RUN-EXE', 'Stopping the process using Popen.terminate()...')
                    process.terminate()
                    stdout, stderr = process.communicate(timeout=5)
                    self._display_message('RUN-EXE', 'Process stopped.')
                except subprocess.TimeoutExpired:
                    # Kill the process.
                    try:
                        self._display_message('RUN-EXE', 'Stopping the process using Popen.kill()...')
                        process.kill()
                        # process.communicate() waits for end-of-file, which may never arrive if there is a child
                        # process still alive. Nothing we can really do about it here, so add a short timeout and
                        # display a warning.
                        stdout, stderr = process.communicate(timeout=1)
                        self._display_message('RUN-EXE', 'Process stopped.')
                    except subprocess.TimeoutExpired:
                        self._display_message('RUN-EXE', 'Failed to stop the process (or its child process(es))!')
            else:
                # We are using psutil.Popen(). First, force-kill all child processes; in onefile mode, this includes
                # the application process, whose termination should trigger cleanup and exit of the parent onefile
                # process.
                self._display_message('RUN-EXE', 'Stopping child processes...')
                for child_process in list(process.children(recursive=True)):
                    with contextlib.suppress(psutil.NoSuchProcess):
                        self._display_message('RUN-EXE', f'Stopping child process {child_process.pid}...')
                        child_process.kill()

                # Give the main process 5 seconds to exit on its own (to accommodate cleanup in onefile mode).
                try:
                    self._display_message('RUN-EXE', f'Waiting for main process ({process.pid}) to stop...')
                    stdout, stderr = process.communicate(timeout=5)
                    self._display_message('RUN-EXE', 'Process stopped on its own.')
                except (psutil.TimeoutExpired, subprocess.TimeoutExpired):
                    # End of the line - kill the main process.
                    self._display_message('RUN-EXE', 'Stopping the process using Popen.kill()...')
                    with contextlib.suppress(psutil.NoSuchProcess):
                        process.kill()
                    # Try to retrieve stdout/stderr - but keep a short timeout, just in case...
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                        self._display_message('RUN-EXE', 'Process stopped.')
                    except (psutil.TimeoutExpired, subprocess.TimeoutExpire):
                        self._display_message('RUN-EXE', 'Failed to stop the process (or its child process(es))!')

        # Display captured stdout/stderr.
        self._display_message('RUN-EXE', 'Captured output:')
        sys.stdout.buffer.write(b"N/A\n" if stdout is None else stdout)
        sys.stderr.buffer.write(b"N/A\n" if stderr is None else stderr)
        self._display_message('RUN-EXE', 'End of captured output.')

        self._display_message('RUN-EXE', f'Done! Return code: {retcode}')

        return retcode

    def _test_building(self, args):
        """
        Run building of test script.

        :param args: additional CLI options for PyInstaller.

        Return True if build succeeded False otherwise.
        """
        if self._is_spec:
            default_args = [
                '--distpath', self._distdir,
                '--workpath', self._builddir,
                '--log-level', 'INFO',
            ]  # yapf: disable
        else:
            default_args = [
                '--debug=bootloader',
                '--noupx',
                '--specpath', self._specdir,
                '--distpath', self._distdir,
                '--workpath', self._builddir,
                '--path', _get_modules_dir(self._request),
                '--log-level', 'INFO',
            ]  # yapf: disable

            # Choose bundle mode.
            if self._mode == 'onedir':
                default_args.append('--onedir')
            elif self._mode == 'onefile':
                default_args.append('--onefile')
            # if self._mode is None then just the spec file was supplied.

        pyi_args = [self.script, *default_args, *args]
        # TODO: fix return code in running PyInstaller programmatically.
        PYI_CONFIG = configure.get_config()
        # Override CACHEDIR for PyInstaller and put it into self.tmpdir
        PYI_CONFIG['cachedir'] = str(self._tmpdir)

        pyi_main.run(pyi_args, PYI_CONFIG)
        retcode = 0

        return retcode == 0

    def _examine_executable(self, exe, toc_log):
        """
        Compare log files (now used mostly by multipackage test_name).

        :return: True if .toc files match
        """
        self._display_message('EXAMINE-EXE', f'Matching against TOC log: {toc_log!r}')
        fname_list = pkg_archive_contents(exe)
        with open(toc_log, 'r', encoding='utf-8') as f:
            pattern_list = eval(f.read())
        # Alphabetical order of patterns.
        pattern_list.sort()
        missing = []
        for pattern in pattern_list:
            for fname in fname_list:
                if re.match(pattern, fname):
                    self._display_message('EXAMINE-EXE', f'Entry found: {pattern!r} --> {fname!r}')
                    break
            else:
                # No matching entry found
                missing.append(pattern)
                self._display_message('EXAMINE-EXE', f'Entry MISSING: {pattern!r}')

        # We expect the missing list to be empty
        return not missing


# Scope 'session' should keep the object unchanged for whole tests. This fixture caches basic module graph dependencies
# that are same for every executable.
@pytest.fixture(scope='session')
def pyi_modgraph():
    # Explicitly set the log level since the plugin `pytest-catchlog` (un-) sets the root logger's level to NOTSET for
    # the setup phase, which will lead to TRACE messages been written out.
    import PyInstaller.log as logging
    logging.logger.setLevel(logging.DEBUG)
    initialize_modgraph()


# Run by default test as onedir and onefile.
@pytest.fixture(params=['onedir', 'onefile'])
def pyi_builder(tmpdir, monkeypatch, request, pyi_modgraph):
    # Save/restore environment variable PATH.
    monkeypatch.setenv('PATH', os.environ['PATH'])
    # PyInstaller or a test case might manipulate 'sys.path'. Reset it for every test.
    monkeypatch.syspath_prepend(None)
    # Set current working directory to
    monkeypatch.chdir(tmpdir)
    # Clean up configuration and force PyInstaller to do a clean configuration for another app/test. The value is same
    # as the original value.
    monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': []})

    yield AppBuilder(tmpdir, request, request.param)

    # Clean up the temporary directory of a successful test
    if _PYI_BUILDER_CLEANUP and request.node.rep_setup.passed and request.node.rep_call.passed:
        if tmpdir.exists():
            tmpdir.remove(rec=1, ignore_errors=True)


# Fixture for .spec based tests. With .spec it does not make sense to differentiate onefile/onedir mode.
@pytest.fixture
def pyi_builder_spec(tmpdir, request, monkeypatch, pyi_modgraph):
    # Save/restore environment variable PATH.
    monkeypatch.setenv('PATH', os.environ['PATH'])
    # Set current working directory to
    monkeypatch.chdir(tmpdir)
    # PyInstaller or a test case might manipulate 'sys.path'. Reset it for every test.
    monkeypatch.syspath_prepend(None)
    # Clean up configuration and force PyInstaller to do a clean configuration for another app/test. The value is same
    # as the original value.
    monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': []})

    yield AppBuilder(tmpdir, request, None)

    # Clean up the temporary directory of a successful test
    if _PYI_BUILDER_CLEANUP and request.node.rep_setup.passed and request.node.rep_call.passed:
        if tmpdir.exists():
            tmpdir.remove(rec=1, ignore_errors=True)


# Define a fixture which compiles the data/load_dll_using_ctypes/ctypes_dylib.c program in the tmpdir, returning the
# tmpdir object.
@pytest.fixture()
def compiled_dylib(tmpdir, request):
    tmp_data_dir = _data_dir_copy(request, 'ctypes_dylib', tmpdir)

    # Compile the ctypes_dylib in the tmpdir: Make tmpdir/data the CWD. Do NOT use monkeypatch.chdir() to change and
    # monkeypatch.undo() to restore the CWD, since this will undo ALL monkeypatches (such as the pyi_builder's additions
    # to sys.path), breaking the test.
    old_wd = tmp_data_dir.chdir()
    try:
        if is_win:
            tmp_data_dir = tmp_data_dir.join('ctypes_dylib.dll')
            # For Mingw-x64 we must pass '-m32' to build 32-bit binaries
            march = '-m32' if architecture == '32bit' else '-m64'
            ret = subprocess.call('gcc -shared ' + march + ' ctypes_dylib.c -o ctypes_dylib.dll', shell=True)
            if ret != 0:
                # Find path to cl.exe file.
                from distutils.msvccompiler import MSVCCompiler
                comp = MSVCCompiler()
                comp.initialize()
                cl_path = comp.cc
                # Fallback to msvc.
                ret = subprocess.call([cl_path, '/LD', 'ctypes_dylib.c'], shell=False)
        elif is_darwin:
            tmp_data_dir = tmp_data_dir.join('ctypes_dylib.dylib')
            # On Mac OS X we need to detect architecture - 32 bit or 64 bit.
            arch = 'arm64' if platform.machine() == 'arm64' else 'i386' if architecture == '32bit' else 'x86_64'
            cmd = (
                'gcc -arch ' + arch + ' -Wall -dynamiclib '
                'ctypes_dylib.c -o ctypes_dylib.dylib -headerpad_max_install_names'
            )
            ret = subprocess.call(cmd, shell=True)
            id_dylib = os.path.abspath('ctypes_dylib.dylib')
            ret = subprocess.call('install_name_tool -id %s ctypes_dylib.dylib' % (id_dylib,), shell=True)
        else:
            tmp_data_dir = tmp_data_dir.join('ctypes_dylib.so')
            ret = subprocess.call('gcc -fPIC -shared ctypes_dylib.c -o ctypes_dylib.so', shell=True)
        assert ret == 0, 'Compile ctypes_dylib failed.'
    finally:
        # Reset the CWD directory.
        old_wd.chdir()

    return tmp_data_dir


@pytest.fixture
def pyi_windowed_builder(pyi_builder: AppBuilder):
    """A pyi_builder equivalent for testing --windowed applications."""

    # psutil.Popen() somehow bypasses an application's windowed/console mode so that any application built in
    # --windowed mode but invoked with psutil still receives valid std{in,out,err} handles and behaves exactly like
    # a console application. In short, testing windowed mode with psutil is a null test. We must instead use subprocess.

    def _run_executable_(args, exe_path, prog_env, prog_cwd, runtime):
        return subprocess.run([exe_path, *args], env=prog_env, cwd=prog_cwd, timeout=runtime).returncode

    pyi_builder._run_executable_ = _run_executable_
    yield pyi_builder
