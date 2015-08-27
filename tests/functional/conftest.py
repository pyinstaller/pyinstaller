#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Futures
# -------
from __future__ import print_function

# Library imports
# ---------------
import copy
import glob
import os
import pytest
import re
import subprocess
import sys
import inspect
import textwrap
import io

# Local imports
# -------------
# Expand sys.path with PyInstaller source.
_ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(_ROOT_DIR)

from PyInstaller import configure
from PyInstaller import main as pyi_main
from PyInstaller.utils.cliutils import archive_viewer
from PyInstaller.compat import is_darwin, is_win, is_py2, safe_repr
from PyInstaller.depend.analysis import initialize_modgraph
from PyInstaller.utils.win32 import winutils

# Globals
# -------
# Directory with Python scripts for functional tests. E.g. main scripts, etc.
_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
# Directory with .toc log files.
_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
# Directory storing test-specific data.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# Provide test access to _DATA_DIR via a fixture.
@pytest.fixture
def data_dir():
    return _DATA_DIR

class AppBuilder(object):

    def __init__(self, tmpdir, bundle_mode, module_graph):
        self._tmpdir = tmpdir
        self._mode = bundle_mode
        self._specdir = self._tmpdir
        self._distdir = os.path.join(self._tmpdir, 'dist')
        self._builddir = os.path.join(self._tmpdir, 'build')
        self._modgraph = module_graph

    def test_source(self, source, *args, **kwargs):
        """
        Test a Python script given as source code.

        The source will be written into a file named like the
        test-function. This file will then be passed to `test_script`.
        If you need other related file, e.g. as `.toc`-file for
        testing the content, put it at at the normal place. Just mind
        to take the basnename from the test-function's name.

        :param script: Source code to create executable from. This
                       will be saved into a temporary file which is
                       then passed on to `test_script`.

        :param test_id: Test-id for parametrized tests. If given, it
                        will be appended to the script filename,
                        separated by two underscores.

        All other arguments are passed streigth on to `test_script`.

        """
        testname = inspect.stack()[1][3]
        if 'test_id' in kwargs:
            # For parametrized test append the test-id.
            testname = testname + '__' + kwargs['test_id']
            del kwargs['test_id']

        scriptfile = os.path.join(os.path.abspath(self._tmpdir),
                                  testname + '.py')
        source = textwrap.dedent(source)
        with io.open(scriptfile, 'w', encoding='utf-8') as ofh:
            print(u'# -*- coding: utf-8 -*-', file=ofh)
            print(source, file=ofh)
        return self.test_script(scriptfile, *args, **kwargs)


    def test_script(self, script, pyi_args=None, app_name=None, app_args=None, runtime=None):
        """
        Main method to wrap all phases of testing a Python script.

        :param script: Name of script to create executable from.
        :param pyi_args: Additional arguments to pass to PyInstaller when creating executable.
        :param app_name: Name of the executable. This is equivalent to argument --name=APPNAME.
        :param app_args: Additional arguments to pass to
        :param runtime: Time in milliseconds how long to keep executable running.
        :param toc_log: List of modules that are expected to be bundled with the executable.
        """
        if pyi_args is None:
            pyi_args = []
        if app_args is None:
            app_args = []

        if app_name:
            pyi_args.extend(['--name', app_name])
        else:
            # Derive name from script name.
            app_name = os.path.splitext(os.path.basename(script))[0]

        self.script = os.path.join(_SCRIPT_DIR, script)
        assert os.path.exists(self.script), 'Script %s not found.' % script

        assert self._test_building(args=pyi_args), 'Building of %s failed.' % script
        self._test_executables(app_name, args=app_args, runtime=runtime)

    def _test_executables(self, name, args, runtime):
        """
        Run created executable to make sure it works.

        Multipackage-tests generate more than one exe-file and all of
        them have to be run.

        :param args: CLI options to pass to the created executable.
        :param runtime: Time in miliseconds how long to keep the executable running.

        :return: Exit code of the executable.
        """
        # TODO implement runtime - kill the app (Ctrl+C) when time times out
        exes = self._find_executables(name)
        # Empty list means that PyInstaller probably failed to create any executable.
        assert exes != [], 'No executable file was found.'
        for exe in exes:
            retcode = self._run_executable(exe, args)
            assert retcode == 0, 'Running exe %s failed with return-code %s.' % (exe, retcode)
            # Try to find .toc log file. .toc log file has the same basename as exe file.
            toc_log = os.path.join(_LOGS_DIR, os.path.basename(exe) + '.toc')
            if os.path.exists(toc_log):
                assert self._examine_executable(exe, toc_log), 'Matching .toc of %s failed.' % exe

    def _find_executables(self, name):
        """
        Search for all executables generated by the testcase.

        If the test-case is called e.g. 'test_multipackage1', this is
        searching for each of 'test_multipackage1.exe' and
        'multipackage1_?.exe' in both one-file- and one-dir-mode.

        :param name: Name of the executable to look for.

        :return: List of executables
        """
        exes = []
        onedir_pt = os.path.join(self._distdir, name, name)
        onefile_pt = os.path.join(self._distdir, name)
        patterns = [onedir_pt, onefile_pt,
                    # Multipackage one-dir
                    onedir_pt + '_?',
                    # Multipackage one-file
                    onefile_pt + '_?']
        # For Windows append .exe extension to patterns.
        if is_win:
            patterns = [pt + '.exe' for pt in patterns]
        # For Mac OS X append pattern for .app bundles.
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

    def _run_executable(self, prog, args):
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

        # Run executable in the directory where it is.
        prog_cwd = os.path.dirname(prog)

        # On Windows, `subprocess.call` does not search in its `cwd` for the
        # executable named as the first argument, so it must be passed as an
        # absolute path. This is documented for the Windows API `CreateProcess`
        if not is_win:
            # The executable will be called as relative not absolute path.
            prog = os.path.join(os.curdir, os.path.basename(prog))

        # Workaround to enable win_codepage_test
        # If _distdir is 'bytes', PyI build fails with ASCII decode error
        # when it joins the 'bytes' _distdir with the 'unicode' filenames from bindep and
        # winmanifest.
        #
        # PyI succeeds with _distdir as 'unicode', but subprocess
        # fails with ASCII encode error. subprocess succeeds if progname is
        # mbcs-encoded 'bytes'
        if is_win and is_py2:
            if isinstance(prog, unicode):
                prog = prog.encode('mbcs')
            if isinstance(prog_cwd, unicode):
                prog_cwd = prog_cwd.encode('mbcs')

        # Run executable. stderr is redirected to stdout.
        print('RUNNING:', safe_repr(prog))
        # Using sys.stdout/sys.stderr for subprocess fixes printing messages in
        # Windows command prompt. Py.test is then able to collect stdout/sterr
        # messages and display them if a test fails.
        retcode = subprocess.call([prog] + args, stdout=sys.stdout, stderr=sys.stderr,
                                  env=prog_env, cwd=prog_cwd)
        return retcode

    def _test_building(self, args):
        """
        Run building of test script.

        :param args: additional CLI options for PyInstaller.

        Return True if build succeded False otherwise.
        """
        default_args = ['--debug', '--noupx',
                '--specpath', self._specdir,
                '--distpath', self._distdir,
                '--workpath', self._builddir]
        default_args.extend(['--debug', '--log-level=DEBUG'])

        # Choose bundle mode.
        if self._mode == 'onedir':
            default_args.append('--onedir')
        elif self._mode == 'onefile':
            default_args.append('--onefile')

        pyi_args = [self.script] + default_args + args
        # TODO fix return code in running PyInstaller programatically
        PYI_CONFIG = configure.get_config(upx_dir=None)
        # Override CONFIGDIR for PyInstaller and put it into self.tmpdir
        PYI_CONFIG['configdir'] = self._tmpdir
        # Speed up tests by reusing copy of basic module graph object.
        PYI_CONFIG['tests_modgraph'] = copy.deepcopy(self._modgraph)
        pyi_main.run(pyi_args, PYI_CONFIG)
        retcode = 0

        return retcode == 0

    def _examine_executable(self, exe, toc_log):
        """
        Compare log files (now used mostly by multipackage test_name).

        :return: True if .toc files match
        """
        print('EXECUTING MATCHING:', toc_log)
        fname_list = archive_viewer.get_archive_content(exe)
        fname_list = [fn for fn in fname_list]
        with open(toc_log, 'rU') as f:
            pattern_list = eval(f.read())
        # Alphabetical order of patterns.
        pattern_list.sort()
        missing = []
        for pattern in pattern_list:
            for fname in fname_list:
                if re.match(pattern, fname):
                    print('MATCH:', pattern, '-->', fname)
                    break
            else:
                # No matching entry found
                missing.append(pattern)
                print('MISSING:', pattern)

        # Not all modules matched.
        # Stop comparing other .toc files and fail the test.
        if missing:
            for m in missing:
                print('Missing', m, 'in', exe)
            return False
        # All patterns matched.
        return True


# Scope 'session' should keep the object unchanged for whole tests.
# This fixture caches basic module graph dependencies that are same
# for every executable.
@pytest.fixture(scope='session')
def pyi_modgraph():
    return initialize_modgraph()


# Run by default test as onedir and onefile.
@pytest.fixture(params=['onedir', 'onefile'])
def pyi_builder(tmpdir, monkeypatch, request, pyi_modgraph):
    tmp = tmpdir.strpath
    # Append _MMODULES_DIR to sys.path for building exes.
    # Some tests need additional test modules.
    # This also ensures that sys.path is reseted to original value for every test.
    monkeypatch.syspath_prepend(_MODULES_DIR)
    # Save/restore environment variable PATH.
    monkeypatch.setenv('PATH', os.environ['PATH'], )
    # Set current working directory to
    monkeypatch.chdir(tmp)

    return AppBuilder(tmp, request.param, pyi_modgraph)
