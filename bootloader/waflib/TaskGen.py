#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import copy, re, os, functools
from waflib import Task, Utils, Logs, Errors, ConfigSet, Node

feats = Utils.defaultdict(set)
HEADER_EXTS = ['.h', '.hpp', '.hxx', '.hh']


class task_gen(object):
    mappings = Utils.ordered_iter_dict()
    prec = Utils.defaultdict(set)

    def __init__(self, *k, **kw):
        self.source = []
        self.target = ''
        self.meths = []
        self.features = []
        self.tasks = []
        if not 'bld' in kw:
            self.env = ConfigSet.ConfigSet()
            self.idx = 0
            self.path = None
        else:
            self.bld = kw['bld']
            self.env = self.bld.env.derive()
            self.path = kw.get('path', self.bld.path)
            path = self.path.abspath()
            try:
                self.idx = self.bld.idx[path] = self.bld.idx.get(path, 0) + 1
            except AttributeError:
                self.bld.idx = {}
                self.idx = self.bld.idx[path] = 1
            try:
                self.tg_idx_count = self.bld.tg_idx_count = self.bld.tg_idx_count + 1
            except AttributeError:
                self.tg_idx_count = self.bld.tg_idx_count = 1
        for key, val in kw.items():
            setattr(self, key, val)

    def __str__(self):
        return "<task_gen %r declared in %s>" % (self.name, self.path.abspath())

    def __repr__(self):
        lst = []
        for x in self.__dict__:
            if x not in ('env', 'bld', 'compiled_tasks', 'tasks'):
                lst.append("%s=%s" % (x, repr(getattr(self, x))))
        return "bld(%s) in %s" % (", ".join(lst), self.path.abspath())

    def get_cwd(self):
        return self.bld.bldnode

    def get_name(self):
        try:
            return self._name
        except AttributeError:
            if isinstance(self.target, list):
                lst = [str(x) for x in self.target]
                name = self._name = ','.join(lst)
            else:
                name = self._name = str(self.target)
            return name

    def set_name(self, name):
        self._name = name

    name = property(get_name, set_name)

    def to_list(self, val):
        if isinstance(val, str):
            return val.split()
        else:
            return val

    def post(self):
        if getattr(self, 'posted', None):
            return False
        self.posted = True
        keys = set(self.meths)
        keys.update(feats['*'])
        self.features = Utils.to_list(self.features)
        for x in self.features:
            st = feats[x]
            if st:
                keys.update(st)
            elif not x in Task.classes:
                Logs.warn('feature %r does not exist - bind at least one method to it?', x)
        prec = {}
        prec_tbl = self.prec
        for x in prec_tbl:
            if x in keys:
                prec[x] = prec_tbl[x]
        tmp = []
        for a in keys:
            for x in prec.values():
                if a in x:
                    break
            else:
                tmp.append(a)
        tmp.sort(reverse=True)
        out = []
        while tmp:
            e = tmp.pop()
            if e in keys:
                out.append(e)
            try:
                nlst = prec[e]
            except KeyError:
                pass
            else:
                del prec[e]
                for x in nlst:
                    for y in prec:
                        if x in prec[y]:
                            break
                    else:
                        tmp.append(x)
                        tmp.sort(reverse=True)
        if prec:
            buf = ['Cycle detected in the method execution:']
            for k, v in prec.items():
                buf.append('- %s after %s' % (k, [x for x in v if x in prec]))
            raise Errors.WafError('\n'.join(buf))
        self.meths = out
        Logs.debug('task_gen: posting %s %d', self, id(self))
        for x in out:
            try:
                v = getattr(self, x)
            except AttributeError:
                raise Errors.WafError('%r is not a valid task generator method' % x)
            Logs.debug('task_gen: -> %s (%d)', x, id(self))
            v()
        Logs.debug('task_gen: posted %s', self.name)
        return True

    def get_hook(self, node):
        name = node.name
        for k in self.mappings:
            try:
                if name.endswith(k):
                    return self.mappings[k]
            except TypeError:
                if k.match(name):
                    return self.mappings[k]
        keys = list(self.mappings.keys())
        raise Errors.WafError("File %r has no mapping in %r (load a waf tool?)" % (node, keys))

    def create_task(self, name, src=None, tgt=None, **kw):
        task = Task.classes[name](env=self.env.derive(), generator=self)
        if src:
            task.set_inputs(src)
        if tgt:
            task.set_outputs(tgt)
        task.__dict__.update(kw)
        self.tasks.append(task)
        return task

    def clone(self, env):
        newobj = self.bld()
        for x in self.__dict__:
            if x in ('env', 'bld'):
                continue
            elif x in ('path', 'features'):
                setattr(newobj, x, getattr(self, x))
            else:
                setattr(newobj, x, copy.copy(getattr(self, x)))
        newobj.posted = False
        if isinstance(env, str):
            newobj.env = self.bld.all_envs[env].derive()
        else:
            newobj.env = env.derive()
        return newobj


def declare_chain(
    name='',
    rule=None,
    reentrant=None,
    color='BLUE',
    ext_in=[],
    ext_out=[],
    before=[],
    after=[],
    decider=None,
    scan=None,
    install_path=None,
    shell=False
):
    ext_in = Utils.to_list(ext_in)
    ext_out = Utils.to_list(ext_out)
    if not name:
        name = rule
    cls = Task.task_factory(
        name, rule, color=color, ext_in=ext_in, ext_out=ext_out, before=before, after=after, scan=scan, shell=shell
    )

    def x_file(self, node):
        if ext_in:
            _ext_in = ext_in[0]
        tsk = self.create_task(name, node)
        cnt = 0
        ext = decider(self, node) if decider else cls.ext_out
        for x in ext:
            k = node.change_ext(x, ext_in=_ext_in)
            tsk.outputs.append(k)
            if reentrant != None:
                if cnt < int(reentrant):
                    self.source.append(k)
            else:
                for y in self.mappings:
                    if k.name.endswith(y):
                        self.source.append(k)
                        break
            cnt += 1
        if install_path:
            self.install_task = self.add_install_files(install_to=install_path, install_from=tsk.outputs)
        return tsk

    for x in cls.ext_in:
        task_gen.mappings[x] = x_file
    return x_file


def taskgen_method(func):
    setattr(task_gen, func.__name__, func)
    return func


def feature(*k):
    def deco(func):
        setattr(task_gen, func.__name__, func)
        for name in k:
            feats[name].update([func.__name__])
        return func

    return deco


def before_method(*k):
    def deco(func):
        setattr(task_gen, func.__name__, func)
        for fun_name in k:
            task_gen.prec[func.__name__].add(fun_name)
        return func

    return deco


before = before_method


def after_method(*k):
    def deco(func):
        setattr(task_gen, func.__name__, func)
        for fun_name in k:
            task_gen.prec[fun_name].add(func.__name__)
        return func

    return deco


after = after_method


def extension(*k):
    def deco(func):
        setattr(task_gen, func.__name__, func)
        for x in k:
            task_gen.mappings[x] = func
        return func

    return deco


@taskgen_method
def to_nodes(self, lst, path=None):
    tmp = []
    path = path or self.path
    find = path.find_resource
    if isinstance(lst, Node.Node):
        lst = [lst]
    for x in Utils.to_list(lst):
        if isinstance(x, str):
            node = find(x)
        elif hasattr(x, 'name'):
            node = x
        else:
            tmp.extend(self.to_nodes(x))
            continue
        if not node:
            raise Errors.WafError('source not found: %r in %r' % (x, self))
        tmp.append(node)
    return tmp


@feature('*')
def process_source(self):
    self.source = self.to_nodes(getattr(self, 'source', []))
    for node in self.source:
        self.get_hook(node)(self, node)


@feature('*')
@before_method('process_source')
def process_rule(self):
    if not getattr(self, 'rule', None):
        return
    name = str(getattr(self, 'name', None) or self.target or getattr(self.rule, '__name__', self.rule))
    try:
        cache = self.bld.cache_rule_attr
    except AttributeError:
        cache = self.bld.cache_rule_attr = {}
    chmod = getattr(self, 'chmod', None)
    shell = getattr(self, 'shell', True)
    color = getattr(self, 'color', 'BLUE')
    scan = getattr(self, 'scan', None)
    _vars = getattr(self, 'vars', [])
    cls_str = getattr(self, 'cls_str', None)
    cls_keyword = getattr(self, 'cls_keyword', None)
    use_cache = getattr(self, 'cache_rule', 'True')
    deep_inputs = getattr(self, 'deep_inputs', False)
    scan_val = has_deps = hasattr(self, 'deps')
    if scan:
        scan_val = id(scan)
    key = Utils.h_list((name, self.rule, chmod, shell, color, cls_str, cls_keyword, scan_val, _vars, deep_inputs))
    cls = None
    if use_cache:
        try:
            cls = cache[key]
        except KeyError:
            pass
    if not cls:
        rule = self.rule
        if chmod is not None:

            def chmod_fun(tsk):
                for x in tsk.outputs:
                    os.chmod(x.abspath(), tsk.generator.chmod)

            if isinstance(rule, tuple):
                rule = list(rule)
                rule.append(chmod_fun)
                rule = tuple(rule)
            else:
                rule = (rule, chmod_fun)
        cls = Task.task_factory(name, rule, _vars, shell=shell, color=color)
        if cls_str:
            setattr(cls, '__str__', self.cls_str)
        if cls_keyword:
            setattr(cls, 'keyword', self.cls_keyword)
        if deep_inputs:
            Task.deep_inputs(cls)
        if scan:
            cls.scan = self.scan
        elif has_deps:

            def scan(self):
                nodes = []
                for x in self.generator.to_list(getattr(self.generator, 'deps', None)):
                    node = self.generator.path.find_resource(x)
                    if not node:
                        self.generator.bld.fatal('Could not find %r (was it declared?)' % x)
                    nodes.append(node)
                return [nodes, []]

            cls.scan = scan
        if use_cache:
            cache[key] = cls
    tsk = self.create_task(name)
    for x in ('after', 'before', 'ext_in', 'ext_out'):
        setattr(tsk, x, getattr(self, x, []))
    if hasattr(self, 'stdout'):
        tsk.stdout = self.stdout
    if hasattr(self, 'stderr'):
        tsk.stderr = self.stderr
    if getattr(self, 'timeout', None):
        tsk.timeout = self.timeout
    if getattr(self, 'always', None):
        tsk.always_run = True
    if getattr(self, 'target', None):
        if isinstance(self.target, str):
            self.target = self.target.split()
        if not isinstance(self.target, list):
            self.target = [self.target]
        for x in self.target:
            if isinstance(x, str):
                tsk.outputs.append(self.path.find_or_declare(x))
            else:
                x.parent.mkdir()
                tsk.outputs.append(x)
        if getattr(self, 'install_path', None):
            self.install_task = self.add_install_files(
                install_to=self.install_path, install_from=tsk.outputs, chmod=getattr(self, 'chmod', Utils.O644)
            )
    if getattr(self, 'source', None):
        tsk.inputs = self.to_nodes(self.source)
        self.source = []
    if getattr(self, 'cwd', None):
        tsk.cwd = self.cwd
    if isinstance(tsk.run, functools.partial):
        tsk.run = functools.partial(tsk.run, tsk)


@feature('seq')
def sequence_order(self):
    if self.meths and self.meths[-1] != 'sequence_order':
        self.meths.append('sequence_order')
        return
    if getattr(self, 'seq_start', None):
        return
    if getattr(self.bld, 'prev', None):
        self.bld.prev.post()
        for x in self.bld.prev.tasks:
            for y in self.tasks:
                y.set_run_after(x)
    self.bld.prev = self


re_m4 = re.compile(r'@(\w+)@', re.M)


class subst_pc(Task.Task):
    def force_permissions(self):
        if getattr(self.generator, 'chmod', None):
            for x in self.outputs:
                os.chmod(x.abspath(), self.generator.chmod)

    def run(self):
        if getattr(self.generator, 'is_copy', None):
            for i, x in enumerate(self.outputs):
                x.write(self.inputs[i].read('rb'), 'wb')
                stat = os.stat(self.inputs[i].abspath())
                os.utime(self.outputs[i].abspath(), (stat.st_atime, stat.st_mtime))
            self.force_permissions()
            return None
        if getattr(self.generator, 'fun', None):
            ret = self.generator.fun(self)
            if not ret:
                self.force_permissions()
            return ret
        code = self.inputs[0].read(encoding=getattr(self.generator, 'encoding', 'latin-1'))
        if getattr(self.generator, 'subst_fun', None):
            code = self.generator.subst_fun(self, code)
            if code is not None:
                self.outputs[0].write(code, encoding=getattr(self.generator, 'encoding', 'latin-1'))
            self.force_permissions()
            return None
        code = code.replace('%', '%%')
        lst = []

        def repl(match):
            g = match.group
            if g(1):
                lst.append(g(1))
                return "%%(%s)s" % g(1)
            return ''

        code = getattr(self.generator, 're_m4', re_m4).sub(repl, code)
        try:
            d = self.generator.dct
        except AttributeError:
            d = {}
            for x in lst:
                tmp = getattr(self.generator, x, '') or self.env[x] or self.env[x.upper()]
                try:
                    tmp = ''.join(tmp)
                except TypeError:
                    tmp = str(tmp)
                d[x] = tmp
        code = code % d
        self.outputs[0].write(code, encoding=getattr(self.generator, 'encoding', 'latin-1'))
        self.generator.bld.raw_deps[self.uid()] = lst
        try:
            delattr(self, 'cache_sig')
        except AttributeError:
            pass
        self.force_permissions()

    def sig_vars(self):
        bld = self.generator.bld
        env = self.env
        upd = self.m.update
        if getattr(self.generator, 'fun', None):
            upd(Utils.h_fun(self.generator.fun).encode())
        if getattr(self.generator, 'subst_fun', None):
            upd(Utils.h_fun(self.generator.subst_fun).encode())
        vars = self.generator.bld.raw_deps.get(self.uid(), [])
        act_sig = bld.hash_env_vars(env, vars)
        upd(act_sig)
        lst = [getattr(self.generator, x, '') for x in vars]
        upd(Utils.h_list(lst))
        return self.m.digest()


@extension('.pc.in')
def add_pcfile(self, node):
    tsk = self.create_task('subst_pc', node, node.change_ext('.pc', '.pc.in'))
    self.install_task = self.add_install_files(
        install_to=getattr(self, 'install_path', '${LIBDIR}/pkgconfig/'), install_from=tsk.outputs
    )


class subst(subst_pc):
    pass


@feature('subst')
@before_method('process_source', 'process_rule')
def process_subst(self):
    src = Utils.to_list(getattr(self, 'source', []))
    if isinstance(src, Node.Node):
        src = [src]
    tgt = Utils.to_list(getattr(self, 'target', []))
    if isinstance(tgt, Node.Node):
        tgt = [tgt]
    if len(src) != len(tgt):
        raise Errors.WafError('invalid number of source/target for %r' % self)
    for x, y in zip(src, tgt):
        if not x or not y:
            raise Errors.WafError('null source or target for %r' % self)
        a, b = None, None
        if isinstance(x, str) and isinstance(y, str) and x == y:
            a = self.path.find_node(x)
            b = self.path.get_bld().make_node(y)
            if not os.path.isfile(b.abspath()):
                b.parent.mkdir()
        else:
            if isinstance(x, str):
                a = self.path.find_resource(x)
            elif isinstance(x, Node.Node):
                a = x
            if isinstance(y, str):
                b = self.path.find_or_declare(y)
            elif isinstance(y, Node.Node):
                b = y
        if not a:
            raise Errors.WafError('could not find %r for %r' % (x, self))
        tsk = self.create_task('subst', a, b)
        for k in ('after', 'before', 'ext_in', 'ext_out'):
            val = getattr(self, k, None)
            if val:
                setattr(tsk, k, val)
        for xt in HEADER_EXTS:
            if b.name.endswith(xt):
                tsk.ext_out = tsk.ext_out + ['.h']
                break
        inst_to = getattr(self, 'install_path', None)
        if inst_to:
            self.install_task = self.add_install_files(
                install_to=inst_to, install_from=b, chmod=getattr(self, 'chmod', Utils.O644)
            )
    self.source = []
