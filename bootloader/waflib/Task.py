#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import os, re, sys, tempfile, traceback
from waflib import Utils, Logs, Errors

NOT_RUN = 0
MISSING = 1
CRASHED = 2
EXCEPTION = 3
CANCELED = 4
SKIPPED = 8
SUCCESS = 9
ASK_LATER = -1
SKIP_ME = -2
RUN_ME = -3
CANCEL_ME = -4
COMPILE_TEMPLATE_SHELL = '''
def f(tsk):
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	cwdx = tsk.get_cwd()
	p = env.get_flat
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	tsk.last_cmd = cmd = \'\'\' %s \'\'\' % s
	return tsk.exec_command(cmd, cwd=cwdx, env=env.env or None)
'''
COMPILE_TEMPLATE_NOSHELL = '''
def f(tsk):
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	cwdx = tsk.get_cwd()
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	def merge(lst1, lst2):
		if lst1 and lst2:
			return lst1[:-1] + [lst1[-1] + lst2[0]] + lst2[1:]
		return lst1 + lst2
	lst = []
	%s
	if '' in lst:
		lst = [x for x in lst if x]
	tsk.last_cmd = lst
	return tsk.exec_command(lst, cwd=cwdx, env=env.env or None)
'''
COMPILE_TEMPLATE_SIG_VARS = '''
def f(tsk):
	sig = tsk.generator.bld.hash_env_vars(tsk.env, tsk.vars)
	tsk.m.update(sig)
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	cwdx = tsk.get_cwd()
	p = env.get_flat
	buf = []
	%s
	tsk.m.update(repr(buf).encode())
'''
classes = {}


class store_task_type(type):
    def __init__(cls, name, bases, dict):
        super(store_task_type, cls).__init__(name, bases, dict)
        name = cls.__name__
        if name != 'evil' and name != 'Task':
            if getattr(cls, 'run_str', None):
                (f, dvars) = compile_fun(cls.run_str, cls.shell)
                cls.hcode = Utils.h_cmd(cls.run_str)
                cls.orig_run_str = cls.run_str
                cls.run_str = None
                cls.run = f
                cls.vars = list(set(cls.vars + dvars))
                cls.vars.sort()
                if cls.vars:
                    fun = compile_sig_vars(cls.vars)
                    if fun:
                        cls.sig_vars = fun
            elif getattr(cls, 'run', None) and not 'hcode' in cls.__dict__:
                cls.hcode = Utils.h_cmd(cls.run)
            getattr(cls, 'register', classes)[name] = cls


evil = store_task_type('evil', (object,), {})


class Task(evil):
    vars = []
    always_run = False
    shell = False
    color = 'GREEN'
    ext_in = []
    ext_out = []
    before = []
    after = []
    hcode = Utils.SIG_NIL
    keep_last_cmd = False
    weight = 0
    tree_weight = 0
    prio_order = 0
    __slots__ = ('hasrun', 'generator', 'env', 'inputs', 'outputs', 'dep_nodes', 'run_after')

    def __init__(self, *k, **kw):
        self.hasrun = NOT_RUN
        try:
            self.generator = kw['generator']
        except KeyError:
            self.generator = self
        self.env = kw['env']
        self.inputs = []
        self.outputs = []
        self.dep_nodes = []
        self.run_after = set()

    def __lt__(self, other):
        return self.priority() > other.priority()

    def __le__(self, other):
        return self.priority() >= other.priority()

    def __gt__(self, other):
        return self.priority() < other.priority()

    def __ge__(self, other):
        return self.priority() <= other.priority()

    def get_cwd(self):
        bld = self.generator.bld
        ret = getattr(self, 'cwd', None) or getattr(bld, 'cwd', bld.bldnode)
        if isinstance(ret, str):
            if os.path.isabs(ret):
                ret = bld.root.make_node(ret)
            else:
                ret = self.generator.path.make_node(ret)
        return ret

    def quote_flag(self, x):
        old = x
        if '\\' in x:
            x = x.replace('\\', '\\\\')
        if '"' in x:
            x = x.replace('"', '\\"')
        if old != x or ' ' in x or '\t' in x or "'" in x:
            x = '"%s"' % x
        return x

    def priority(self):
        return (self.weight + self.prio_order, -getattr(self.generator, 'tg_idx_count', 0))

    def split_argfile(self, cmd):
        return ([cmd[0]], [self.quote_flag(x) for x in cmd[1:]])

    def exec_command(self, cmd, **kw):
        if not 'cwd' in kw:
            kw['cwd'] = self.get_cwd()
        if hasattr(self, 'timeout'):
            kw['timeout'] = self.timeout
        if self.env.PATH:
            env = kw['env'] = dict(kw.get('env') or self.env.env or os.environ)
            env['PATH'] = self.env.PATH if isinstance(self.env.PATH, str) else os.pathsep.join(self.env.PATH)
        if hasattr(self, 'stdout'):
            kw['stdout'] = self.stdout
        if hasattr(self, 'stderr'):
            kw['stderr'] = self.stderr
        if not isinstance(cmd, str):
            if Utils.is_win32:
                too_long = sum([len(arg) for arg in cmd]) + len(cmd) > 8192
            else:
                too_long = len(cmd) > 200000
            if too_long and getattr(self, 'allow_argsfile', True):
                cmd, args = self.split_argfile(cmd)
                try:
                    (fd, tmp) = tempfile.mkstemp()
                    os.write(fd, '\r\n'.join(args).encode())
                    os.close(fd)
                    if Logs.verbose:
                        Logs.debug('argfile: @%r -> %r', tmp, args)
                    return self.generator.bld.exec_command(cmd + ['@' + tmp], **kw)
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
        return self.generator.bld.exec_command(cmd, **kw)

    def process(self):
        try:
            del self.generator.bld.task_sigs[self.uid()]
        except KeyError:
            pass
        try:
            ret = self.run()
        except Exception:
            self.err_msg = traceback.format_exc()
            self.hasrun = EXCEPTION
        else:
            if ret:
                self.err_code = ret
                self.hasrun = CRASHED
            else:
                try:
                    self.post_run()
                except Errors.WafError:
                    pass
                except Exception:
                    self.err_msg = traceback.format_exc()
                    self.hasrun = EXCEPTION
                else:
                    self.hasrun = SUCCESS
        if self.hasrun != SUCCESS and self.scan:
            try:
                del self.generator.bld.imp_sigs[self.uid()]
            except KeyError:
                pass

    def log_display(self, bld):
        if self.generator.bld.progress_bar == 3:
            return
        s = self.display()
        if s:
            if bld.logger:
                logger = bld.logger
            else:
                logger = Logs
            if self.generator.bld.progress_bar == 1:
                c1 = Logs.colors.cursor_off
                c2 = Logs.colors.cursor_on
                logger.info(s, extra={'stream': sys.stderr, 'terminator': '', 'c1': c1, 'c2': c2})
            else:
                logger.info(s, extra={'terminator': '', 'c1': '', 'c2': ''})

    def display(self):
        col1 = Logs.colors(self.color)
        col2 = Logs.colors.NORMAL
        master = self.generator.bld.producer

        def cur():
            return master.processed - master.ready.qsize()

        if self.generator.bld.progress_bar == 1:
            return self.generator.bld.progress_line(cur(), master.total, col1, col2)
        if self.generator.bld.progress_bar == 2:
            ela = str(self.generator.bld.timer)
            try:
                ins = ','.join([n.name for n in self.inputs])
            except AttributeError:
                ins = ''
            try:
                outs = ','.join([n.name for n in self.outputs])
            except AttributeError:
                outs = ''
            return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n' % (master.total, cur(), ins, outs, ela)
        s = str(self)
        if not s:
            return None
        total = master.total
        n = len(str(total))
        fs = '[%%%dd/%%%dd] %%s%%s%%s%%s\n' % (n, n)
        kw = self.keyword()
        if kw:
            kw += ' '
        return fs % (cur(), total, kw, col1, s, col2)

    def hash_constraints(self):
        return (
            tuple(self.before), tuple(self.after), tuple(self.ext_in), tuple(self.ext_out), self.__class__.__name__,
            self.hcode
        )

    def format_error(self):
        if Logs.verbose:
            msg = ': %r\n%r' % (self, getattr(self, 'last_cmd', ''))
        else:
            msg = ' (run with -v to display more information)'
        name = getattr(self.generator, 'name', '')
        if getattr(self, "err_msg", None):
            return self.err_msg
        elif not self.hasrun:
            return 'task in %r was not executed for some reason: %r' % (name, self)
        elif self.hasrun == CRASHED:
            try:
                return ' -> task in %r failed with exit status %r%s' % (name, self.err_code, msg)
            except AttributeError:
                return ' -> task in %r failed%s' % (name, msg)
        elif self.hasrun == MISSING:
            return ' -> missing files in %r%s' % (name, msg)
        elif self.hasrun == CANCELED:
            return ' -> %r canceled because of missing dependencies' % name
        else:
            return 'invalid status for task in %r: %r' % (name, self.hasrun)

    def colon(self, var1, var2):
        tmp = self.env[var1]
        if not tmp:
            return []
        if isinstance(var2, str):
            it = self.env[var2]
        else:
            it = var2
        if isinstance(tmp, str):
            return [tmp % x for x in it]
        else:
            lst = []
            for y in it:
                lst.extend(tmp)
                lst.append(y)
            return lst

    def __str__(self):
        name = self.__class__.__name__
        if self.outputs:
            if name.endswith(('lib', 'program')) or not self.inputs:
                node = self.outputs[0]
                return node.path_from(node.ctx.launch_node())
        if not (self.inputs or self.outputs):
            return self.__class__.__name__
        if len(self.inputs) == 1:
            node = self.inputs[0]
            return node.path_from(node.ctx.launch_node())
        src_str = ' '.join([a.path_from(a.ctx.launch_node()) for a in self.inputs])
        tgt_str = ' '.join([a.path_from(a.ctx.launch_node()) for a in self.outputs])
        if self.outputs:
            sep = ' -> '
        else:
            sep = ''
        return '%s: %s%s%s' % (self.__class__.__name__, src_str, sep, tgt_str)

    def keyword(self):
        name = self.__class__.__name__
        if name.endswith(('lib', 'program')):
            return 'Linking'
        if len(self.inputs) == 1 and len(self.outputs) == 1:
            return 'Compiling'
        if not self.inputs:
            if self.outputs:
                return 'Creating'
            else:
                return 'Running'
        return 'Processing'

    def __repr__(self):
        try:
            ins = ",".join([x.name for x in self.inputs])
            outs = ",".join([x.name for x in self.outputs])
        except AttributeError:
            ins = ",".join([str(x) for x in self.inputs])
            outs = ",".join([str(x) for x in self.outputs])
        return "".join(['\n\t{task %r: ' % id(self), self.__class__.__name__, " ", ins, " -> ", outs, '}'])

    def uid(self):
        try:
            return self.uid_
        except AttributeError:
            m = Utils.md5(self.__class__.__name__)
            up = m.update
            for x in self.inputs + self.outputs:
                up(x.abspath())
            self.uid_ = m.digest()
            return self.uid_

    def set_inputs(self, inp):
        if isinstance(inp, list):
            self.inputs += inp
        else:
            self.inputs.append(inp)

    def set_outputs(self, out):
        if isinstance(out, list):
            self.outputs += out
        else:
            self.outputs.append(out)

    def set_run_after(self, task):
        assert isinstance(task, Task)
        self.run_after.add(task)

    def signature(self):
        try:
            return self.cache_sig
        except AttributeError:
            pass
        self.m = Utils.md5(self.hcode)
        self.sig_explicit_deps()
        self.sig_vars()
        if self.scan:
            try:
                self.sig_implicit_deps()
            except Errors.TaskRescan:
                return self.signature()
        ret = self.cache_sig = self.m.digest()
        return ret

    def runnable_status(self):
        bld = self.generator.bld
        if bld.is_install < 0:
            return SKIP_ME
        for t in self.run_after:
            if not t.hasrun:
                return ASK_LATER
            elif t.hasrun < SKIPPED:
                return CANCEL_ME
        try:
            new_sig = self.signature()
        except Errors.TaskNotReady:
            return ASK_LATER
        key = self.uid()
        try:
            prev_sig = bld.task_sigs[key]
        except KeyError:
            Logs.debug('task: task %r must run: it was never run before or the task code changed', self)
            return RUN_ME
        if new_sig != prev_sig:
            Logs.debug('task: task %r must run: the task signature changed', self)
            return RUN_ME
        for node in self.outputs:
            sig = bld.node_sigs.get(node)
            if not sig:
                Logs.debug('task: task %r must run: an output node has no signature', self)
                return RUN_ME
            if sig != key:
                Logs.debug('task: task %r must run: an output node was produced by another task', self)
                return RUN_ME
            if not node.exists():
                Logs.debug('task: task %r must run: an output node does not exist', self)
                return RUN_ME
        return (self.always_run and RUN_ME) or SKIP_ME

    def post_run(self):
        bld = self.generator.bld
        for node in self.outputs:
            if not node.exists():
                self.hasrun = MISSING
                self.err_msg = '-> missing file: %r' % node.abspath()
                raise Errors.WafError(self.err_msg)
            bld.node_sigs[node] = self.uid()
        bld.task_sigs[self.uid()] = self.signature()
        if not self.keep_last_cmd:
            try:
                del self.last_cmd
            except AttributeError:
                pass

    def sig_explicit_deps(self):
        bld = self.generator.bld
        upd = self.m.update
        for x in self.inputs + self.dep_nodes:
            upd(x.get_bld_sig())
        if bld.deps_man:
            additional_deps = bld.deps_man
            for x in self.inputs + self.outputs:
                try:
                    d = additional_deps[x]
                except KeyError:
                    continue
                for v in d:
                    try:
                        v = v.get_bld_sig()
                    except AttributeError:
                        if hasattr(v, '__call__'):
                            v = v()
                    upd(v)

    def sig_deep_inputs(self):
        bld = self.generator.bld
        lst = [bld.task_sigs[bld.node_sigs[node]] for node in (self.inputs + self.dep_nodes) if node.is_bld()]
        self.m.update(Utils.h_list(lst))

    def sig_vars(self):
        sig = self.generator.bld.hash_env_vars(self.env, self.vars)
        self.m.update(sig)

    scan = None

    def sig_implicit_deps(self):
        bld = self.generator.bld
        key = self.uid()
        prev = bld.imp_sigs.get(key, [])
        if prev:
            try:
                if prev == self.compute_sig_implicit_deps():
                    return prev
            except Errors.TaskNotReady:
                raise
            except EnvironmentError:
                for x in bld.node_deps.get(self.uid(), []):
                    if not x.is_bld() and not x.exists():
                        try:
                            del x.parent.children[x.name]
                        except KeyError:
                            pass
            del bld.imp_sigs[key]
            raise Errors.TaskRescan('rescan')
        (bld.node_deps[key], bld.raw_deps[key]) = self.scan()
        if Logs.verbose:
            Logs.debug('deps: scanner for %s: %r; unresolved: %r', self, bld.node_deps[key], bld.raw_deps[key])
        try:
            bld.imp_sigs[key] = self.compute_sig_implicit_deps()
        except EnvironmentError:
            for k in bld.node_deps.get(self.uid(), []):
                if not k.exists():
                    Logs.warn(
                        'Dependency %r for %r is missing: check the task declaration and the build order!', k, self
                    )
            raise

    def compute_sig_implicit_deps(self):
        upd = self.m.update
        self.are_implicit_nodes_ready()
        for k in self.generator.bld.node_deps.get(self.uid(), []):
            upd(k.get_bld_sig())
        return self.m.digest()

    def are_implicit_nodes_ready(self):
        bld = self.generator.bld
        try:
            cache = bld.dct_implicit_nodes
        except AttributeError:
            bld.dct_implicit_nodes = cache = {}
        try:
            dct = cache[bld.current_group]
        except KeyError:
            dct = cache[bld.current_group] = {}
            for tsk in bld.cur_tasks:
                for x in tsk.outputs:
                    dct[x] = tsk
        modified = False
        for x in bld.node_deps.get(self.uid(), []):
            if x in dct:
                self.run_after.add(dct[x])
                modified = True
        if modified:
            for tsk in self.run_after:
                if not tsk.hasrun:
                    raise Errors.TaskNotReady('not ready')


if sys.hexversion > 0x3000000:

    def uid(self):
        try:
            return self.uid_
        except AttributeError:
            m = Utils.md5(self.__class__.__name__.encode('latin-1', 'xmlcharrefreplace'))
            up = m.update
            for x in self.inputs + self.outputs:
                up(x.abspath().encode('latin-1', 'xmlcharrefreplace'))
            self.uid_ = m.digest()
            return self.uid_

    uid.__doc__ = Task.uid.__doc__
    Task.uid = uid


def is_before(t1, t2):
    to_list = Utils.to_list
    for k in to_list(t2.ext_in):
        if k in to_list(t1.ext_out):
            return 1
    if t1.__class__.__name__ in to_list(t2.after):
        return 1
    if t2.__class__.__name__ in to_list(t1.before):
        return 1
    return 0


def set_file_constraints(tasks):
    ins = Utils.defaultdict(set)
    outs = Utils.defaultdict(set)
    for x in tasks:
        for a in x.inputs:
            ins[a].add(x)
        for a in x.dep_nodes:
            ins[a].add(x)
        for a in x.outputs:
            outs[a].add(x)
    links = set(ins.keys()).intersection(outs.keys())
    for k in links:
        for a in ins[k]:
            a.run_after.update(outs[k])


class TaskGroup(object):
    def __init__(self, prev, next):
        self.prev = prev
        self.next = next
        self.done = False

    def get_hasrun(self):
        for k in self.prev:
            if not k.hasrun:
                return NOT_RUN
        return SUCCESS

    hasrun = property(get_hasrun, None)


def set_precedence_constraints(tasks):
    cstr_groups = Utils.defaultdict(list)
    for x in tasks:
        h = x.hash_constraints()
        cstr_groups[h].append(x)
    keys = list(cstr_groups.keys())
    maxi = len(keys)
    for i in range(maxi):
        t1 = cstr_groups[keys[i]][0]
        for j in range(i + 1, maxi):
            t2 = cstr_groups[keys[j]][0]
            if is_before(t1, t2):
                a = i
                b = j
            elif is_before(t2, t1):
                a = j
                b = i
            else:
                continue
            a = cstr_groups[keys[a]]
            b = cstr_groups[keys[b]]
            if len(a) < 2 or len(b) < 2:
                for x in b:
                    x.run_after.update(a)
            else:
                group = TaskGroup(set(a), set(b))
                for x in b:
                    x.run_after.add(group)


def funex(c):
    dc = {}
    exec(c, dc)
    return dc['f']


re_cond = re.compile(r'(?P<var>\w+)|(?P<or>\|)|(?P<and>&)')
re_novar = re.compile(r'^(SRC|TGT)\W+.*?$')
reg_act = re.compile(r'(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})', re.M)


def compile_fun_shell(line):
    extr = []

    def repl(match):
        g = match.group
        if g('dollar'):
            return "$"
        elif g('backslash'):
            return '\\\\'
        elif g('subst'):
            extr.append((g('var'), g('code')))
            return "%s"
        return None

    line = reg_act.sub(repl, line) or line
    dvars = []

    def add_dvar(x):
        if x not in dvars:
            dvars.append(x)

    def replc(m):
        if m.group('and'):
            return ' and '
        elif m.group('or'):
            return ' or '
        else:
            x = m.group('var')
            add_dvar(x)
            return 'env[%r]' % x

    parm = []
    app = parm.append
    for (var, meth) in extr:
        if var == 'SRC':
            if meth:
                app('tsk.inputs%s' % meth)
            else:
                app('" ".join([a.path_from(cwdx) for a in tsk.inputs])')
        elif var == 'TGT':
            if meth:
                app('tsk.outputs%s' % meth)
            else:
                app('" ".join([a.path_from(cwdx) for a in tsk.outputs])')
        elif meth:
            if meth.startswith(':'):
                add_dvar(var)
                m = meth[1:]
                if m == 'SRC':
                    m = '[a.path_from(cwdx) for a in tsk.inputs]'
                elif m == 'TGT':
                    m = '[a.path_from(cwdx) for a in tsk.outputs]'
                elif re_novar.match(m):
                    m = '[tsk.inputs%s]' % m[3:]
                elif re_novar.match(m):
                    m = '[tsk.outputs%s]' % m[3:]
                else:
                    add_dvar(m)
                    if m[:3] not in ('tsk', 'gen', 'bld'):
                        m = '%r' % m
                app('" ".join(tsk.colon(%r, %s))' % (var, m))
            elif meth.startswith('?'):
                expr = re_cond.sub(replc, meth[1:])
                app('p(%r) if (%s) else ""' % (var, expr))
            else:
                call = '%s%s' % (var, meth)
                add_dvar(call)
                app(call)
        else:
            add_dvar(var)
            app("p('%s')" % var)
    if parm:
        parm = "%% (%s) " % (',\n\t\t'.join(parm))
    else:
        parm = ''
    c = COMPILE_TEMPLATE_SHELL % (line, parm)
    Logs.debug('action: %s', c.strip().splitlines())
    return (funex(c), dvars)


reg_act_noshell = re.compile(
    r"(?P<space>\s+)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})|(?P<text>([^$ \t\n\r\f\v]|\$\$)+)", re.M
)


def compile_fun_noshell(line):
    buf = []
    dvars = []
    merge = False
    app = buf.append

    def add_dvar(x):
        if x not in dvars:
            dvars.append(x)

    def replc(m):
        if m.group('and'):
            return ' and '
        elif m.group('or'):
            return ' or '
        else:
            x = m.group('var')
            add_dvar(x)
            return 'env[%r]' % x

    for m in reg_act_noshell.finditer(line):
        if m.group('space'):
            merge = False
            continue
        elif m.group('text'):
            app('[%r]' % m.group('text').replace('$$', '$'))
        elif m.group('subst'):
            var = m.group('var')
            code = m.group('code')
            if var == 'SRC':
                if code:
                    app('[tsk.inputs%s]' % code)
                else:
                    app('[a.path_from(cwdx) for a in tsk.inputs]')
            elif var == 'TGT':
                if code:
                    app('[tsk.outputs%s]' % code)
                else:
                    app('[a.path_from(cwdx) for a in tsk.outputs]')
            elif code:
                if code.startswith(':'):
                    add_dvar(var)
                    m = code[1:]
                    if m == 'SRC':
                        m = '[a.path_from(cwdx) for a in tsk.inputs]'
                    elif m == 'TGT':
                        m = '[a.path_from(cwdx) for a in tsk.outputs]'
                    elif re_novar.match(m):
                        m = '[tsk.inputs%s]' % m[3:]
                    elif re_novar.match(m):
                        m = '[tsk.outputs%s]' % m[3:]
                    else:
                        add_dvar(m)
                        if m[:3] not in ('tsk', 'gen', 'bld'):
                            m = '%r' % m
                    app('tsk.colon(%r, %s)' % (var, m))
                elif code.startswith('?'):
                    expr = re_cond.sub(replc, code[1:])
                    app('to_list(env[%r] if (%s) else [])' % (var, expr))
                else:
                    call = '%s%s' % (var, code)
                    add_dvar(call)
                    app('to_list(%s)' % call)
            else:
                app('to_list(env[%r])' % var)
                add_dvar(var)
        if merge:
            tmp = 'merge(%s, %s)' % (buf[-2], buf[-1])
            del buf[-1]
            buf[-1] = tmp
        merge = True
    buf = ['lst.extend(%s)' % x for x in buf]
    fun = COMPILE_TEMPLATE_NOSHELL % "\n\t".join(buf)
    Logs.debug('action: %s', fun.strip().splitlines())
    return (funex(fun), dvars)


def compile_fun(line, shell=False):
    if isinstance(line, str):
        if line.find('<') > 0 or line.find('>') > 0 or line.find('&&') > 0:
            shell = True
    else:
        dvars_lst = []
        funs_lst = []
        for x in line:
            if isinstance(x, str):
                fun, dvars = compile_fun(x, shell)
                dvars_lst += dvars
                funs_lst.append(fun)
            else:
                funs_lst.append(x)

        def composed_fun(task):
            for x in funs_lst:
                ret = x(task)
                if ret:
                    return ret
            return None

        return composed_fun, dvars_lst
    if shell:
        return compile_fun_shell(line)
    else:
        return compile_fun_noshell(line)


def compile_sig_vars(vars):
    buf = []
    for x in sorted(vars):
        if x[:3] in ('tsk', 'gen', 'bld'):
            buf.append('buf.append(%s)' % x)
    if buf:
        return funex(COMPILE_TEMPLATE_SIG_VARS % '\n\t'.join(buf))
    return None


def task_factory(
    name, func=None, vars=None, color='GREEN', ext_in=[], ext_out=[], before=[], after=[], shell=False, scan=None
):
    params = {
        'vars': vars or [],
        'color': color,
        'name': name,
        'shell': shell,
        'scan': scan,
    }
    if isinstance(func, str) or isinstance(func, tuple):
        params['run_str'] = func
    else:
        params['run'] = func
    cls = type(Task)(name, (Task,), params)
    classes[name] = cls
    if ext_in:
        cls.ext_in = Utils.to_list(ext_in)
    if ext_out:
        cls.ext_out = Utils.to_list(ext_out)
    if before:
        cls.before = Utils.to_list(before)
    if after:
        cls.after = Utils.to_list(after)
    return cls


def deep_inputs(cls):
    def sig_explicit_deps(self):
        Task.sig_explicit_deps(self)
        Task.sig_deep_inputs(self)

    cls.sig_explicit_deps = sig_explicit_deps
    return cls


TaskBase = Task


class TaskSemaphore(object):
    def __init__(self, num):
        self.num = num
        self.locking = set()
        self.waiting = set()

    def is_locked(self):
        return len(self.locking) >= self.num

    def acquire(self, tsk):
        if self.is_locked():
            raise IndexError('Cannot lock more %r' % self.locking)
        self.locking.add(tsk)

    def release(self, tsk):
        self.locking.remove(tsk)
