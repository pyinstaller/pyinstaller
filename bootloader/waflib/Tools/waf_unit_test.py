#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import os, shlex, sys
from waflib.TaskGen import feature, after_method, taskgen_method
from waflib import Utils, Task, Logs, Options
from waflib.Tools import ccroot

testlock = Utils.threading.Lock()
SCRIPT_TEMPLATE = """#! %(python)s
import subprocess, sys
cmd = %(cmd)r
# if you want to debug with gdb:
#cmd = ['gdb', '-args'] + cmd
env = %(env)r
status = subprocess.call(cmd, env=env, cwd=%(cwd)r, shell=isinstance(cmd, str))
sys.exit(status)
"""


@taskgen_method
def handle_ut_cwd(self, key):
    cwd = getattr(self, key, None)
    if cwd:
        if isinstance(cwd, str):
            if os.path.isabs(cwd):
                self.ut_cwd = self.bld.root.make_node(cwd)
            else:
                self.ut_cwd = self.path.make_node(cwd)


@feature('test_scripts')
def make_interpreted_test(self):
    for x in ['test_scripts_source', 'test_scripts_template']:
        if not hasattr(self, x):
            Logs.warn('a test_scripts taskgen i missing %s' % x)
            return
    self.ut_run, lst = Task.compile_fun(self.test_scripts_template, shell=getattr(self, 'test_scripts_shell', False))
    script_nodes = self.to_nodes(self.test_scripts_source)
    for script_node in script_nodes:
        tsk = self.create_task('utest', [script_node])
        tsk.vars = lst + tsk.vars
        tsk.env['SCRIPT'] = script_node.path_from(tsk.get_cwd())
    self.handle_ut_cwd('test_scripts_cwd')
    env = getattr(self, 'test_scripts_env', None)
    if env:
        self.ut_env = env
    else:
        self.ut_env = dict(os.environ)
    paths = getattr(self, 'test_scripts_paths', {})
    for (k, v) in paths.items():
        p = self.ut_env.get(k, '').split(os.pathsep)
        if isinstance(v, str):
            v = v.split(os.pathsep)
        self.ut_env[k] = os.pathsep.join(p + v)


@feature('test')
@after_method('apply_link', 'process_use')
def make_test(self):
    if not getattr(self, 'link_task', None):
        return
    tsk = self.create_task('utest', self.link_task.outputs)
    if getattr(self, 'ut_str', None):
        self.ut_run, lst = Task.compile_fun(self.ut_str, shell=getattr(self, 'ut_shell', False))
        tsk.vars = lst + tsk.vars
    self.handle_ut_cwd('ut_cwd')
    if not hasattr(self, 'ut_paths'):
        paths = []
        for x in self.tmp_use_sorted:
            try:
                y = self.bld.get_tgen_by_name(x).link_task
            except AttributeError:
                pass
            else:
                if not isinstance(y, ccroot.stlink_task):
                    paths.append(y.outputs[0].parent.abspath())
        self.ut_paths = os.pathsep.join(paths) + os.pathsep
    if not hasattr(self, 'ut_env'):
        self.ut_env = dct = dict(os.environ)

        def add_path(var):
            dct[var] = self.ut_paths + dct.get(var, '')

        if Utils.is_win32:
            add_path('PATH')
        elif Utils.unversioned_sys_platform() == 'darwin':
            add_path('DYLD_LIBRARY_PATH')
            add_path('LD_LIBRARY_PATH')
        else:
            add_path('LD_LIBRARY_PATH')
    if not hasattr(self, 'ut_cmd'):
        self.ut_cmd = getattr(Options.options, 'testcmd', False)


@taskgen_method
def add_test_results(self, tup):
    Logs.debug("ut: %r", tup)
    try:
        self.utest_results.append(tup)
    except AttributeError:
        self.utest_results = [tup]
    try:
        self.bld.utest_results.append(tup)
    except AttributeError:
        self.bld.utest_results = [tup]


@Task.deep_inputs
class utest(Task.Task):
    color = 'PINK'
    after = ['vnum', 'inst']
    vars = []

    def runnable_status(self):
        if getattr(Options.options, 'no_tests', False):
            return Task.SKIP_ME
        ret = super(utest, self).runnable_status()
        if ret == Task.SKIP_ME:
            if getattr(Options.options, 'all_tests', False):
                return Task.RUN_ME
        return ret

    def get_test_env(self):
        return self.generator.ut_env

    def post_run(self):
        super(utest, self).post_run()
        if getattr(Options.options, 'clear_failed_tests', False) and self.waf_unit_test_results[1]:
            self.generator.bld.task_sigs[self.uid()] = None

    def run(self):
        if hasattr(self.generator, 'ut_run'):
            return self.generator.ut_run(self)
        self.ut_exec = getattr(self.generator, 'ut_exec', [self.inputs[0].abspath()])
        ut_cmd = getattr(self.generator, 'ut_cmd', False)
        if ut_cmd:
            self.ut_exec = shlex.split(ut_cmd % ' '.join(self.ut_exec))
        return self.exec_command(self.ut_exec)

    def exec_command(self, cmd, **kw):
        self.generator.bld.log_command(cmd, kw)
        if getattr(Options.options, 'dump_test_scripts', False):
            script_code = SCRIPT_TEMPLATE % {
                'python': sys.executable,
                'env': self.get_test_env(),
                'cwd': self.get_cwd().abspath(),
                'cmd': cmd
            }
            script_file = self.inputs[0].abspath() + '_run.py'
            Utils.writef(script_file, script_code, encoding='utf-8')
            os.chmod(script_file, Utils.O755)
            if Logs.verbose > 1:
                Logs.info('Test debug file written as %r' % script_file)
        proc = Utils.subprocess.Popen(
            cmd,
            cwd=self.get_cwd().abspath(),
            env=self.get_test_env(),
            stderr=Utils.subprocess.PIPE,
            stdout=Utils.subprocess.PIPE,
            shell=isinstance(cmd, str)
        )
        (stdout, stderr) = proc.communicate()
        self.waf_unit_test_results = tup = (self.inputs[0].abspath(), proc.returncode, stdout, stderr)
        testlock.acquire()
        try:
            return self.generator.add_test_results(tup)
        finally:
            testlock.release()

    def get_cwd(self):
        return getattr(self.generator, 'ut_cwd', self.inputs[0].parent)


def summary(bld):
    lst = getattr(bld, 'utest_results', [])
    if lst:
        Logs.pprint('CYAN', 'execution summary')
        total = len(lst)
        tfail = len([x for x in lst if x[1]])
        Logs.pprint('GREEN', '  tests that pass %d/%d' % (total - tfail, total))
        for (f, code, out, err) in lst:
            if not code:
                Logs.pprint('GREEN', '    %s' % f)
        Logs.pprint('GREEN' if tfail == 0 else 'RED', '  tests that fail %d/%d' % (tfail, total))
        for (f, code, out, err) in lst:
            if code:
                Logs.pprint('RED', '    %s' % f)


def set_exit_code(bld):
    lst = getattr(bld, 'utest_results', [])
    for (f, code, out, err) in lst:
        if code:
            msg = []
            if out:
                msg.append('stdout:%s%s' % (os.linesep, out.decode('utf-8')))
            if err:
                msg.append('stderr:%s%s' % (os.linesep, err.decode('utf-8')))
            bld.fatal(os.linesep.join(msg))


def options(opt):
    opt.add_option('--notests', action='store_true', default=False, help='Exec no unit tests', dest='no_tests')
    opt.add_option('--alltests', action='store_true', default=False, help='Exec all unit tests', dest='all_tests')
    opt.add_option(
        '--clear-failed',
        action='store_true',
        default=False,
        help='Force failed unit tests to run again next time',
        dest='clear_failed_tests'
    )
    opt.add_option(
        '--testcmd',
        action='store',
        default=False,
        dest='testcmd',
        help=
        'Run the unit tests using the test-cmd string example "--testcmd="valgrind --error-exitcode=1 %s" to run under valgrind'
    )
    opt.add_option(
        '--dump-test-scripts',
        action='store_true',
        default=False,
        help='Create python scripts to help debug tests',
        dest='dump_test_scripts'
    )
