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

import pytest  # noqa: E402

from PyInstaller import __main__ as pyi_main  # noqa: E402
from PyInstaller import configure  # noqa: E402
from PyInstaller.compat import is_cygwin, is_darwin, is_win  # noqa: E402
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
    return request.path.resolve().parent  # pathlib.Path instance


# Directory with Python scripts for functional tests.
def _get_script_dir(request):
    return _get_base_dir(request) / 'scripts'


# Directory with testing modules used in some tests.
def _get_modules_dir(request):
    return _get_base_dir(request) / 'modules'


# Directory with .toc log files.
def _get_logs_dir(request):
    return _get_base_dir(request) / 'logs'


# Return the directory where data for tests is located.
def _get_data_dir(request):
    return _get_base_dir(request) / 'data'


# Directory with .spec files used in some tests.
def _get_spec_dir(request):
    return _get_base_dir(request) / 'specs'


@pytest.fixture
def spec_dir(request):
    """
    Return the directory where the test spec-files reside.
    """
    return _get_spec_dir(request)


@pytest.fixture
def script_dir(request):
    """
    Return the directory where the test scripts reside.
    """
    return _get_script_dir(request)


# A fixture that copies test's data directory into test's temporary directory. The data directory is assumed to be
# `data/{test-name}` found next to the .py file that contains test.
@pytest.fixture
def data_dir(
    # The request object for this test. Used to infer name of the test and location of the source .py file.
    # See
    # https://pytest.org/latest/builtin.html#_pytest.python.FixtureRequest
    # and
    # https://pytest.org/latest/fixture.html#fixtures-can-introspect-the-requesting-test-context.
    request,
    # The tmp_path object for this test. See: https://pytest.org/latest/tmp_path.html.
    tmp_path
):
    # Strip the leading 'test_' from the test's name.
    test_name = request.function.__name__[5:]

    # Copy to data dir and return the path.
    source_data_dir = _get_data_dir(request) / test_name
    tmp_data_dir = tmp_path / 'data'
    # Copy the data.
    shutil.copytree(source_data_dir, tmp_data_dir)
    # Return the temporary data directory, so that the copied data can now be used.
    return tmp_data_dir


class AppBuilder:
    def __init__(self, tmp_path, request, bundle_mode):
        self._tmp_path = tmp_path
        self._request = request
        self._mode = bundle_mode
        self._spec_dir = tmp_path
        self._dist_dir = tmp_path / 'dist'
        self._build_dir = tmp_path / 'build'
        self._is_spec = False

    def test_spec(self, specfile, *args, **kwargs):
        """
        Test a Python script that is referenced in the supplied .spec file.
        """
        __tracebackhide__ = True
        specfile = _get_spec_dir(self._request) / specfile
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
        """
        __tracebackhide__ = True
        # For parametrized test append the test-id.
        scriptfile = gen_sourcefile(self._tmp_path, source, kwargs.setdefault('test_id'))
        del kwargs['test_id']
        return self.test_script(scriptfile, *args, **kwargs)

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
            script = _get_script_dir(self._request) / script
        self.script = str(script)  # might be a pathlib.Path at this point!
        assert os.path.exists(self.script), f'Script {self.script!r} not found.'

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
            toc_log = os.path.splitext(os.path.basename(exe))[0] + '.toc'
            toc_log = _get_logs_dir(self._request) / toc_log
            if toc_log.exists():
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
        onedir_pt = str(self._dist_dir / name / name)
        onefile_pt = str(self._dist_dir / name)
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
        # For macOS append pattern for .app bundles.
        if is_darwin:
            # e.g:  ./dist/name.app/Contents/MacOS/name
            app_bundle_pt = str(self._dist_dir / f'{name}.app' / 'Contents' / 'MacOS' / name)
            patterns.append(app_bundle_pt)
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
        # Same for Cygwin - if /usr/bin is not in PATH, cygwin1.dll cannot be discovered.
        if is_cygwin:
            prog_env['PATH'] = os.pathsep.join(['/usr/local/bin', '/usr/bin'])
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
            prog_cwd = str(self._tmp_path)
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
        process = popen_implementation(args, executable=exe_path, env=prog_env, cwd=prog_cwd)

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
                '--distpath', str(self._dist_dir),
                '--workpath', str(self._build_dir),
                '--log-level', 'INFO',
            ]  # yapf: disable
        else:
            default_args = [
                '--debug=bootloader',
                '--noupx',
                '--specpath', str(self._spec_dir),
                '--distpath', str(self._dist_dir),
                '--workpath', str(self._build_dir),
                '--path', str(_get_modules_dir(self._request)),
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
        # Override CACHEDIR for PyInstaller; relocate cache into `self._tmp_path`.
        PYI_CONFIG['cachedir'] = str(self._tmp_path)

        pyi_main.run(pyi_args, PYI_CONFIG)
        retcode = 0

        return retcode == 0

    def _examine_executable(self, exe, toc_log):
        """
        Compare log files (now used mostly by multipackage test_name).

        :return: True if .toc files match
        """
        self._display_message('EXAMINE-EXE', f'Matching against TOC log: {str(toc_log)!r}')
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
def pyi_builder(tmp_path, monkeypatch, request, pyi_modgraph):
    # Save/restore environment variable PATH.
    monkeypatch.setenv('PATH', os.environ['PATH'])
    # PyInstaller or a test case might manipulate 'sys.path'. Reset it for every test.
    monkeypatch.syspath_prepend(None)
    # Set current working directory to
    monkeypatch.chdir(tmp_path)
    # Clean up configuration and force PyInstaller to do a clean configuration for another app/test. The value is same
    # as the original value.
    monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': []})

    yield AppBuilder(tmp_path, request, request.param)

    # Clean up the temporary directory of a successful test
    if _PYI_BUILDER_CLEANUP and request.node.rep_setup.passed and request.node.rep_call.passed:
        if tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)


# Fixture for .spec based tests. With .spec it does not make sense to differentiate onefile/onedir mode.
@pytest.fixture
def pyi_builder_spec(tmp_path, request, monkeypatch, pyi_modgraph):
    # Save/restore environment variable PATH.
    monkeypatch.setenv('PATH', os.environ['PATH'])
    # Set current working directory to
    monkeypatch.chdir(tmp_path)
    # PyInstaller or a test case might manipulate 'sys.path'. Reset it for every test.
    monkeypatch.syspath_prepend(None)
    # Clean up configuration and force PyInstaller to do a clean configuration for another app/test. The value is same
    # as the original value.
    monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': []})

    yield AppBuilder(tmp_path, request, None)

    # Clean up the temporary directory of a successful test
    if _PYI_BUILDER_CLEANUP and request.node.rep_setup.passed and request.node.rep_call.passed:
        if tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)


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
