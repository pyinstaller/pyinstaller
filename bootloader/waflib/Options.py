#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import os, tempfile, optparse, sys, re
from waflib import Logs, Utils, Context, Errors

options = optparse.Values()
commands = []
envvars = []
lockfile = os.environ.get('WAFLOCK', '.lock-waf_%s_build' % sys.platform)


class opt_parser(optparse.OptionParser):
    def __init__(self, ctx, allow_unknown=False):
        optparse.OptionParser.__init__(
            self,
            conflict_handler='resolve',
            add_help_option=False,
            version='%s %s (%s)' % (Context.WAFNAME, Context.WAFVERSION, Context.WAFREVISION)
        )
        self.formatter.width = Logs.get_term_cols()
        self.ctx = ctx
        self.allow_unknown = allow_unknown

    def _process_args(self, largs, rargs, values):
        while rargs:
            try:
                optparse.OptionParser._process_args(self, largs, rargs, values)
            except (optparse.BadOptionError, optparse.AmbiguousOptionError) as e:
                if self.allow_unknown:
                    largs.append(e.opt_str)
                else:
                    self.error(str(e))

    def _process_long_opt(self, rargs, values):
        if self.allow_unknown:
            back = [] + rargs
            try:
                optparse.OptionParser._process_long_opt(self, rargs, values)
            except optparse.BadOptionError:
                while rargs:
                    rargs.pop()
                rargs.extend(back)
                rargs.pop(0)
                raise
        else:
            optparse.OptionParser._process_long_opt(self, rargs, values)

    def print_usage(self, file=None):
        return self.print_help(file)

    def get_usage(self):
        cmds_str = {}
        for cls in Context.classes:
            if not cls.cmd or cls.cmd == 'options' or cls.cmd.startswith('_'):
                continue
            s = cls.__doc__ or ''
            cmds_str[cls.cmd] = s
        if Context.g_module:
            for (k, v) in Context.g_module.__dict__.items():
                if k in ('options', 'init', 'shutdown'):
                    continue
                if type(v) is type(Context.create_context):
                    if v.__doc__ and not k.startswith('_'):
                        cmds_str[k] = v.__doc__
        just = 0
        for k in cmds_str:
            just = max(just, len(k))
        lst = ['  %s: %s' % (k.ljust(just), v) for (k, v) in cmds_str.items()]
        lst.sort()
        ret = '\n'.join(lst)
        return '''%s [commands] [options]

Main commands (example: ./%s build -j4)
%s
''' % (Context.WAFNAME, Context.WAFNAME, ret)


class OptionsContext(Context.Context):
    cmd = 'options'
    fun = 'options'

    def __init__(self, **kw):
        super(OptionsContext, self).__init__(**kw)
        self.parser = opt_parser(self)
        self.option_groups = {}
        jobs = self.jobs()
        p = self.add_option
        color = os.environ.get('NOCOLOR', '') and 'no' or 'auto'
        if os.environ.get('CLICOLOR', '') == '0':
            color = 'no'
        elif os.environ.get('CLICOLOR_FORCE', '') == '1':
            color = 'yes'
        p(
            '-c',
            '--color',
            dest='colors',
            default=color,
            action='store',
            help='whether to use colors (yes/no/auto) [default: auto]',
            choices=('yes', 'no', 'auto')
        )
        p('-j', '--jobs', dest='jobs', default=jobs, type='int', help='amount of parallel jobs (%r)' % jobs)
        p('-k', '--keep', dest='keep', default=0, action='count', help='continue despite errors (-kk to try harder)')
        p(
            '-v',
            '--verbose',
            dest='verbose',
            default=0,
            action='count',
            help='verbosity level -v -vv or -vvv [default: 0]'
        )
        p('--zones', dest='zones', default='', action='store', help='debugging zones (task_gen, deps, tasks, etc)')
        p('--profile', dest='profile', default=0, action='store_true', help=optparse.SUPPRESS_HELP)
        p('--pdb', dest='pdb', default=0, action='store_true', help=optparse.SUPPRESS_HELP)
        p('-h', '--help', dest='whelp', default=0, action='store_true', help="show this help message and exit")
        gr = self.add_option_group('Configuration options')
        self.option_groups['configure options'] = gr
        gr.add_option('-o', '--out', action='store', default='', help='build dir for the project', dest='out')
        gr.add_option('-t', '--top', action='store', default='', help='src dir for the project', dest='top')
        gr.add_option(
            '--no-lock-in-run',
            action='store_true',
            default=os.environ.get('NO_LOCK_IN_RUN', ''),
            help=optparse.SUPPRESS_HELP,
            dest='no_lock_in_run'
        )
        gr.add_option(
            '--no-lock-in-out',
            action='store_true',
            default=os.environ.get('NO_LOCK_IN_OUT', ''),
            help=optparse.SUPPRESS_HELP,
            dest='no_lock_in_out'
        )
        gr.add_option(
            '--no-lock-in-top',
            action='store_true',
            default=os.environ.get('NO_LOCK_IN_TOP', ''),
            help=optparse.SUPPRESS_HELP,
            dest='no_lock_in_top'
        )
        default_prefix = getattr(Context.g_module, 'default_prefix', os.environ.get('PREFIX'))
        if not default_prefix:
            if Utils.unversioned_sys_platform() == 'win32':
                d = tempfile.gettempdir()
                default_prefix = d[0].upper() + d[1:]
            else:
                default_prefix = '/usr/local/'
        gr.add_option(
            '--prefix',
            dest='prefix',
            default=default_prefix,
            help='installation prefix [default: %r]' % default_prefix
        )
        gr.add_option('--bindir', dest='bindir', help='bindir')
        gr.add_option('--libdir', dest='libdir', help='libdir')
        gr = self.add_option_group('Build and installation options')
        self.option_groups['build and install options'] = gr
        gr.add_option(
            '-p',
            '--progress',
            dest='progress_bar',
            default=0,
            action='count',
            help='-p: progress bar; -pp: ide output'
        )
        gr.add_option(
            '--targets', dest='targets', default='', action='store', help='task generators, e.g. "target1,target2"'
        )
        gr = self.add_option_group('Step options')
        self.option_groups['step options'] = gr
        gr.add_option(
            '--files',
            dest='files',
            default='',
            action='store',
            help='files to process, by regexp, e.g. "*/main.c,*/test/main.o"'
        )
        default_destdir = os.environ.get('DESTDIR', '')
        gr = self.add_option_group('Installation and uninstallation options')
        self.option_groups['install/uninstall options'] = gr
        gr.add_option(
            '--destdir',
            help='installation root [default: %r]' % default_destdir,
            default=default_destdir,
            dest='destdir'
        )
        gr.add_option('-f', '--force', dest='force', default=False, action='store_true', help='force file installation')
        gr.add_option(
            '--distcheck-args', metavar='ARGS', help='arguments to pass to distcheck', default=None, action='store'
        )

    def jobs(self):
        count = int(os.environ.get('JOBS', 0))
        if count < 1:
            if 'NUMBER_OF_PROCESSORS' in os.environ:
                count = int(os.environ.get('NUMBER_OF_PROCESSORS', 1))
            else:
                if hasattr(os, 'sysconf_names'):
                    if 'SC_NPROCESSORS_ONLN' in os.sysconf_names:
                        count = int(os.sysconf('SC_NPROCESSORS_ONLN'))
                    elif 'SC_NPROCESSORS_CONF' in os.sysconf_names:
                        count = int(os.sysconf('SC_NPROCESSORS_CONF'))
                if not count and os.name not in ('nt', 'java'):
                    try:
                        tmp = self.cmd_and_log(['sysctl', '-n', 'hw.ncpu'], quiet=0)
                    except Errors.WafError:
                        pass
                    else:
                        if re.match('^[0-9]+$', tmp):
                            count = int(tmp)
        if count < 1:
            count = 1
        elif count > 1024:
            count = 1024
        return count

    def add_option(self, *k, **kw):
        return self.parser.add_option(*k, **kw)

    def add_option_group(self, *k, **kw):
        try:
            gr = self.option_groups[k[0]]
        except KeyError:
            gr = self.parser.add_option_group(*k, **kw)
        self.option_groups[k[0]] = gr
        return gr

    def get_option_group(self, opt_str):
        try:
            return self.option_groups[opt_str]
        except KeyError:
            for group in self.parser.option_groups:
                if group.title == opt_str:
                    return group
            return None

    def sanitize_path(self, path, cwd=None):
        if not cwd:
            cwd = Context.launch_dir
        p = os.path.expanduser(path)
        p = os.path.join(cwd, p)
        p = os.path.normpath(p)
        p = os.path.abspath(p)
        return p

    def parse_cmd_args(self, _args=None, cwd=None, allow_unknown=False):
        self.parser.allow_unknown = allow_unknown
        (options, leftover_args) = self.parser.parse_args(args=_args)
        envvars = []
        commands = []
        for arg in leftover_args:
            if '=' in arg:
                envvars.append(arg)
            elif arg != 'options':
                commands.append(arg)
        if options.jobs < 1:
            options.jobs = 1
        for name in 'top out destdir prefix bindir libdir'.split():
            if getattr(options, name, None):
                path = self.sanitize_path(getattr(options, name), cwd)
                setattr(options, name, path)
        return options, commands, envvars

    def init_module_vars(self, arg_options, arg_commands, arg_envvars):
        options.__dict__.clear()
        del commands[:]
        del envvars[:]
        options.__dict__.update(arg_options.__dict__)
        commands.extend(arg_commands)
        envvars.extend(arg_envvars)
        for var in envvars:
            (name, value) = var.split('=', 1)
            os.environ[name.strip()] = value

    def init_logs(self, options, commands, envvars):
        Logs.verbose = options.verbose
        if options.verbose >= 1:
            self.load('errcheck')
        colors = {'yes': 2, 'auto': 1, 'no': 0}[options.colors]
        Logs.enable_colors(colors)
        if options.zones:
            Logs.zones = options.zones.split(',')
            if not Logs.verbose:
                Logs.verbose = 1
        elif Logs.verbose > 0:
            Logs.zones = ['runner']
        if Logs.verbose > 2:
            Logs.zones = ['*']

    def parse_args(self, _args=None):
        options, commands, envvars = self.parse_cmd_args()
        self.init_logs(options, commands, envvars)
        self.init_module_vars(options, commands, envvars)

    def execute(self):
        super(OptionsContext, self).execute()
        self.parse_args()
        Utils.alloc_process_pool(options.jobs)
