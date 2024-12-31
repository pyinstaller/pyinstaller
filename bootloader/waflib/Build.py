#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import os, sys, errno, re, shutil, stat
try:
    import cPickle
except ImportError:
    import pickle as cPickle
from waflib import Node, Runner, TaskGen, Utils, ConfigSet, Task, Logs, Options, Context, Errors

CACHE_DIR = 'c4che'
CACHE_SUFFIX = '_cache.py'
INSTALL = 1337
UNINSTALL = -1337
SAVED_ATTRS = 'root node_sigs task_sigs imp_sigs raw_deps node_deps'.split()
CFG_FILES = 'cfg_files'
POST_AT_ONCE = 0
POST_LAZY = 1
PROTOCOL = -1
if sys.platform == 'cli':
    PROTOCOL = 0


class BuildContext(Context.Context):
    '''executes the build'''
    cmd = 'build'
    variant = ''

    def __init__(self, **kw):
        super(BuildContext, self).__init__(**kw)
        self.is_install = 0
        self.top_dir = kw.get('top_dir', Context.top_dir)
        self.out_dir = kw.get('out_dir', Context.out_dir)
        self.run_dir = kw.get('run_dir', Context.run_dir)
        self.launch_dir = Context.launch_dir
        self.post_mode = POST_LAZY
        self.cache_dir = kw.get('cache_dir')
        if not self.cache_dir:
            self.cache_dir = os.path.join(self.out_dir, CACHE_DIR)
        self.all_envs = {}
        self.node_sigs = {}
        self.task_sigs = {}
        self.imp_sigs = {}
        self.node_deps = {}
        self.raw_deps = {}
        self.task_gen_cache_names = {}
        self.jobs = Options.options.jobs
        self.targets = Options.options.targets
        self.keep = Options.options.keep
        self.progress_bar = Options.options.progress_bar
        self.deps_man = Utils.defaultdict(list)
        self.current_group = 0
        self.groups = []
        self.group_names = {}
        for v in SAVED_ATTRS:
            if not hasattr(self, v):
                setattr(self, v, {})

    def get_variant_dir(self):
        if not self.variant:
            return self.out_dir
        return os.path.join(self.out_dir, os.path.normpath(self.variant))

    variant_dir = property(get_variant_dir, None)

    def __call__(self, *k, **kw):
        kw['bld'] = self
        ret = TaskGen.task_gen(*k, **kw)
        self.task_gen_cache_names = {}
        self.add_to_group(ret, group=kw.get('group'))
        return ret

    def __copy__(self):
        raise Errors.WafError('build contexts cannot be copied')

    def load_envs(self):
        node = self.root.find_node(self.cache_dir)
        if not node:
            raise Errors.WafError('The project was not configured: run "waf configure" first!')
        lst = node.ant_glob('**/*%s' % CACHE_SUFFIX, quiet=True)
        if not lst:
            raise Errors.WafError('The cache directory is empty: reconfigure the project')
        for x in lst:
            name = x.path_from(node).replace(CACHE_SUFFIX, '').replace('\\', '/')
            env = ConfigSet.ConfigSet(x.abspath())
            self.all_envs[name] = env
            for f in env[CFG_FILES]:
                newnode = self.root.find_resource(f)
                if not newnode or not newnode.exists():
                    raise Errors.WafError('Missing configuration file %r, reconfigure the project!' % f)

    def init_dirs(self):
        if not (os.path.isabs(self.top_dir) and os.path.isabs(self.out_dir)):
            raise Errors.WafError('The project was not configured: run "waf configure" first!')
        self.path = self.srcnode = self.root.find_dir(self.top_dir)
        self.bldnode = self.root.make_node(self.variant_dir)
        self.bldnode.mkdir()

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()
        self.execute_build()

    def execute_build(self):
        Logs.info("Waf: Entering directory `%s'", self.variant_dir)
        self.recurse([self.run_dir])
        self.pre_build()
        self.timer = Utils.Timer()
        try:
            self.compile()
        finally:
            if self.progress_bar == 1 and sys.stderr.isatty():
                c = self.producer.processed or 1
                m = self.progress_line(c, c, Logs.colors.BLUE, Logs.colors.NORMAL)
                Logs.info(m, extra={'stream': sys.stderr, 'c1': Logs.colors.cursor_off, 'c2': Logs.colors.cursor_on})
            Logs.info("Waf: Leaving directory `%s'", self.variant_dir)
        try:
            self.producer.bld = None
            del self.producer
        except AttributeError:
            pass
        self.post_build()

    def restore(self):
        try:
            env = ConfigSet.ConfigSet(os.path.join(self.cache_dir, 'build.config.py'))
        except EnvironmentError:
            pass
        else:
            if env.version < Context.HEXVERSION:
                raise Errors.WafError('Project was configured with a different version of Waf, please reconfigure it')
            for t in env.tools:
                self.setup(**t)
        dbfn = os.path.join(self.variant_dir, Context.DBFILE)
        try:
            data = Utils.readf(dbfn, 'rb')
        except (EnvironmentError, EOFError):
            Logs.debug('build: Could not load the build cache %s (missing)', dbfn)
        else:
            try:
                Node.pickle_lock.acquire()
                Node.Nod3 = self.node_class
                try:
                    data = cPickle.loads(data)
                except Exception as e:
                    Logs.debug('build: Could not pickle the build cache %s: %r', dbfn, e)
                else:
                    for x in SAVED_ATTRS:
                        setattr(self, x, data.get(x, {}))
            finally:
                Node.pickle_lock.release()
        self.init_dirs()

    def store(self):
        data = {}
        for x in SAVED_ATTRS:
            data[x] = getattr(self, x)
        db = os.path.join(self.variant_dir, Context.DBFILE)
        try:
            Node.pickle_lock.acquire()
            Node.Nod3 = self.node_class
            x = cPickle.dumps(data, PROTOCOL)
        finally:
            Node.pickle_lock.release()
        Utils.writef(db + '.tmp', x, m='wb')
        try:
            st = os.stat(db)
            os.remove(db)
            if not Utils.is_win32:
                os.chown(db + '.tmp', st.st_uid, st.st_gid)
        except (AttributeError, OSError):
            pass
        os.rename(db + '.tmp', db)

    def compile(self):
        Logs.debug('build: compile()')
        self.producer = Runner.Parallel(self, self.jobs)
        self.producer.biter = self.get_build_iterator()
        try:
            self.producer.start()
        except KeyboardInterrupt:
            if self.is_dirty():
                self.store()
            raise
        else:
            if self.is_dirty():
                self.store()
        if self.producer.error:
            raise Errors.BuildError(self.producer.error)

    def is_dirty(self):
        return self.producer.dirty

    def setup(self, tool, tooldir=None, funs=None):
        if isinstance(tool, list):
            for i in tool:
                self.setup(i, tooldir)
            return
        module = Context.load_tool(tool, tooldir)
        if hasattr(module, "setup"):
            module.setup(self)

    def get_env(self):
        try:
            return self.all_envs[self.variant]
        except KeyError:
            return self.all_envs['']

    def set_env(self, val):
        self.all_envs[self.variant] = val

    env = property(get_env, set_env)

    def add_manual_dependency(self, path, value):
        if not path:
            raise ValueError('Invalid input path %r' % path)
        if isinstance(path, Node.Node):
            node = path
        elif os.path.isabs(path):
            node = self.root.find_resource(path)
        else:
            node = self.path.find_resource(path)
        if not node:
            raise ValueError('Could not find the path %r' % path)
        if isinstance(value, list):
            self.deps_man[node].extend(value)
        else:
            self.deps_man[node].append(value)

    def launch_node(self):
        try:
            return self.p_ln
        except AttributeError:
            self.p_ln = self.root.find_dir(self.launch_dir)
            return self.p_ln

    def hash_env_vars(self, env, vars_lst):
        if not env.table:
            env = env.parent
            if not env:
                return Utils.SIG_NIL
        idx = str(id(env)) + str(vars_lst)
        try:
            cache = self.cache_env
        except AttributeError:
            cache = self.cache_env = {}
        else:
            try:
                return self.cache_env[idx]
            except KeyError:
                pass
        lst = [env[a] for a in vars_lst]
        cache[idx] = ret = Utils.h_list(lst)
        Logs.debug('envhash: %s %r', Utils.to_hex(ret), lst)
        return ret

    def get_tgen_by_name(self, name):
        cache = self.task_gen_cache_names
        if not cache:
            for g in self.groups:
                for tg in g:
                    try:
                        cache[tg.name] = tg
                    except AttributeError:
                        pass
        try:
            return cache[name]
        except KeyError:
            raise Errors.WafError('Could not find a task generator for the name %r' % name)

    def progress_line(self, idx, total, col1, col2):
        if not sys.stderr.isatty():
            return ''
        n = len(str(total))
        Utils.rot_idx += 1
        ind = Utils.rot_chr[Utils.rot_idx % 4]
        pc = (100. * idx) / total
        fs = "[%%%dd/%%d][%%s%%2d%%%%%%s][%s][" % (n, ind)
        left = fs % (idx, total, col1, pc, col2)
        right = '][%s%s%s]' % (col1, self.timer, col2)
        cols = Logs.get_term_cols() - len(left) - len(right) + 2 * len(col1) + 2 * len(col2)
        if cols < 7:
            cols = 7
        ratio = ((cols * idx) // total) - 1
        bar = ('=' * ratio + '>').ljust(cols)
        msg = Logs.indicator % (left, bar, right)
        return msg

    def declare_chain(self, *k, **kw):
        return TaskGen.declare_chain(*k, **kw)

    def pre_build(self):
        for m in getattr(self, 'pre_funs', []):
            m(self)

    def post_build(self):
        for m in getattr(self, 'post_funs', []):
            m(self)

    def add_pre_fun(self, meth):
        try:
            self.pre_funs.append(meth)
        except AttributeError:
            self.pre_funs = [meth]

    def add_post_fun(self, meth):
        try:
            self.post_funs.append(meth)
        except AttributeError:
            self.post_funs = [meth]

    def get_group(self, x):
        if not self.groups:
            self.add_group()
        if x is None:
            return self.groups[self.current_group]
        if x in self.group_names:
            return self.group_names[x]
        return self.groups[x]

    def add_to_group(self, tgen, group=None):
        assert (isinstance(tgen, TaskGen.task_gen) or isinstance(tgen, Task.Task))
        tgen.bld = self
        self.get_group(group).append(tgen)

    def get_group_name(self, g):
        if not isinstance(g, list):
            g = self.groups[g]
        for x in self.group_names:
            if id(self.group_names[x]) == id(g):
                return x
        return ''

    def get_group_idx(self, tg):
        se = id(tg)
        for i, tmp in enumerate(self.groups):
            for t in tmp:
                if id(t) == se:
                    return i
        return None

    def add_group(self, name=None, move=True):
        if name and name in self.group_names:
            raise Errors.WafError('add_group: name %s already present', name)
        g = []
        self.group_names[name] = g
        self.groups.append(g)
        if move:
            self.current_group = len(self.groups) - 1

    def set_group(self, idx):
        if isinstance(idx, str):
            g = self.group_names[idx]
            for i, tmp in enumerate(self.groups):
                if id(g) == id(tmp):
                    self.current_group = i
                    break
        else:
            self.current_group = idx

    def total(self):
        total = 0
        for group in self.groups:
            for tg in group:
                try:
                    total += len(tg.tasks)
                except AttributeError:
                    total += 1
        return total

    def get_targets(self):
        to_post = []
        min_grp = 0
        for name in self.targets.split(','):
            tg = self.get_tgen_by_name(name)
            m = self.get_group_idx(tg)
            if m > min_grp:
                min_grp = m
                to_post = [tg]
            elif m == min_grp:
                to_post.append(tg)
        return (min_grp, to_post)

    def get_all_task_gen(self):
        lst = []
        for g in self.groups:
            lst.extend(g)
        return lst

    def post_group(self):
        def tgpost(tg):
            try:
                f = tg.post
            except AttributeError:
                pass
            else:
                f()

        if self.targets == '*':
            for tg in self.groups[self.current_group]:
                tgpost(tg)
        elif self.targets:
            if self.current_group < self._min_grp:
                for tg in self.groups[self.current_group]:
                    tgpost(tg)
            else:
                for tg in self._exact_tg:
                    tg.post()
        else:
            ln = self.launch_node()
            if ln.is_child_of(self.bldnode):
                Logs.warn('Building from the build directory, forcing --targets=*')
                ln = self.srcnode
            elif not ln.is_child_of(self.srcnode):
                Logs.warn(
                    'CWD %s is not under %s, forcing --targets=* (run distclean?)', ln.abspath(), self.srcnode.abspath()
                )
                ln = self.srcnode

            def is_post(tg, ln):
                try:
                    p = tg.path
                except AttributeError:
                    pass
                else:
                    if p.is_child_of(ln):
                        return True

            def is_post_group():
                for i, g in enumerate(self.groups):
                    if i > self.current_group:
                        for tg in g:
                            if is_post(tg, ln):
                                return True

            if self.post_mode == POST_LAZY and ln != self.srcnode:
                if is_post_group():
                    ln = self.srcnode
            for tg in self.groups[self.current_group]:
                if is_post(tg, ln):
                    tgpost(tg)

    def get_tasks_group(self, idx):
        tasks = []
        for tg in self.groups[idx]:
            try:
                tasks.extend(tg.tasks)
            except AttributeError:
                tasks.append(tg)
        return tasks

    def get_build_iterator(self):
        if self.targets and self.targets != '*':
            (self._min_grp, self._exact_tg) = self.get_targets()
        if self.post_mode != POST_LAZY:
            for self.current_group, _ in enumerate(self.groups):
                self.post_group()
        for self.current_group, _ in enumerate(self.groups):
            if self.post_mode != POST_AT_ONCE:
                self.post_group()
            tasks = self.get_tasks_group(self.current_group)
            Task.set_file_constraints(tasks)
            Task.set_precedence_constraints(tasks)
            self.cur_tasks = tasks
            if tasks:
                yield tasks
        while 1:
            yield []

    def install_files(self, dest, files, **kw):
        assert (dest)
        tg = self(features='install_task', install_to=dest, install_from=files, **kw)
        tg.dest = tg.install_to
        tg.type = 'install_files'
        if not kw.get('postpone', True):
            tg.post()
        return tg

    def install_as(self, dest, srcfile, **kw):
        assert (dest)
        tg = self(features='install_task', install_to=dest, install_from=srcfile, **kw)
        tg.dest = tg.install_to
        tg.type = 'install_as'
        if not kw.get('postpone', True):
            tg.post()
        return tg

    def symlink_as(self, dest, src, **kw):
        assert (dest)
        tg = self(features='install_task', install_to=dest, install_from=src, **kw)
        tg.dest = tg.install_to
        tg.type = 'symlink_as'
        tg.link = src
        if not kw.get('postpone', True):
            tg.post()
        return tg


@TaskGen.feature('install_task')
@TaskGen.before_method('process_rule', 'process_source')
def process_install_task(self):
    self.add_install_task(**self.__dict__)


@TaskGen.taskgen_method
def add_install_task(self, **kw):
    if not self.bld.is_install:
        return
    if not kw['install_to']:
        return
    if kw['type'] == 'symlink_as' and Utils.is_win32:
        if kw.get('win32_install'):
            kw['type'] = 'install_as'
        else:
            return
    tsk = self.install_task = self.create_task('inst')
    tsk.chmod = kw.get('chmod', Utils.O644)
    tsk.link = kw.get('link', '') or kw.get('install_from', '')
    tsk.relative_trick = kw.get('relative_trick', False)
    tsk.type = kw['type']
    tsk.install_to = tsk.dest = kw['install_to']
    tsk.install_from = kw['install_from']
    tsk.relative_base = kw.get('cwd') or kw.get('relative_base', self.path)
    tsk.install_user = kw.get('install_user')
    tsk.install_group = kw.get('install_group')
    tsk.init_files()
    if not kw.get('postpone', True):
        tsk.run_now()
    return tsk


@TaskGen.taskgen_method
def add_install_files(self, **kw):
    kw['type'] = 'install_files'
    return self.add_install_task(**kw)


@TaskGen.taskgen_method
def add_install_as(self, **kw):
    kw['type'] = 'install_as'
    return self.add_install_task(**kw)


@TaskGen.taskgen_method
def add_symlink_as(self, **kw):
    kw['type'] = 'symlink_as'
    return self.add_install_task(**kw)


class inst(Task.Task):
    def __str__(self):
        return ''

    def uid(self):
        lst = self.inputs + self.outputs + [self.link, self.generator.path.abspath()]
        return Utils.h_list(lst)

    def init_files(self):
        if self.type == 'symlink_as':
            inputs = []
        else:
            inputs = self.generator.to_nodes(self.install_from)
            if self.type == 'install_as':
                assert len(inputs) == 1
        self.set_inputs(inputs)
        dest = self.get_install_path()
        outputs = []
        if self.type == 'symlink_as':
            if self.relative_trick:
                self.link = os.path.relpath(self.link, os.path.dirname(dest))
            outputs.append(self.generator.bld.root.make_node(dest))
        elif self.type == 'install_as':
            outputs.append(self.generator.bld.root.make_node(dest))
        else:
            for y in inputs:
                if self.relative_trick:
                    destfile = os.path.join(dest, y.path_from(self.relative_base))
                else:
                    destfile = os.path.join(dest, y.name)
                outputs.append(self.generator.bld.root.make_node(destfile))
        self.set_outputs(outputs)

    def runnable_status(self):
        ret = super(inst, self).runnable_status()
        if ret == Task.SKIP_ME and self.generator.bld.is_install:
            return Task.RUN_ME
        return ret

    def post_run(self):
        pass

    def get_install_path(self, destdir=True):
        if isinstance(self.install_to, Node.Node):
            dest = self.install_to.abspath()
        else:
            dest = os.path.normpath(Utils.subst_vars(self.install_to, self.env))
        if not os.path.isabs(dest):
            dest = os.path.join(self.env.PREFIX, dest)
        if destdir and Options.options.destdir:
            dest = os.path.join(Options.options.destdir, os.path.splitdrive(dest)[1].lstrip(os.sep))
        return dest

    def copy_fun(self, src, tgt):
        if Utils.is_win32 and len(tgt) > 259 and not tgt.startswith('\\\\?\\'):
            tgt = '\\\\?\\' + tgt
        shutil.copy2(src, tgt)
        self.fix_perms(tgt)

    def rm_empty_dirs(self, tgt):
        while tgt:
            tgt = os.path.dirname(tgt)
            try:
                os.rmdir(tgt)
            except OSError:
                break

    def run(self):
        is_install = self.generator.bld.is_install
        if not is_install:
            return
        for x in self.outputs:
            if is_install == INSTALL:
                x.parent.mkdir()
        if self.type == 'symlink_as':
            fun = is_install == INSTALL and self.do_link or self.do_unlink
            fun(self.link, self.outputs[0].abspath())
        else:
            fun = is_install == INSTALL and self.do_install or self.do_uninstall
            launch_node = self.generator.bld.launch_node()
            for x, y in zip(self.inputs, self.outputs):
                fun(x.abspath(), y.abspath(), x.path_from(launch_node))

    def run_now(self):
        status = self.runnable_status()
        if status not in (Task.RUN_ME, Task.SKIP_ME):
            raise Errors.TaskNotReady('Could not process %r: status %r' % (self, status))
        self.run()
        self.hasrun = Task.SUCCESS

    def do_install(self, src, tgt, lbl, **kw):
        if not Options.options.force:
            try:
                st1 = os.stat(tgt)
                st2 = os.stat(src)
            except OSError:
                pass
            else:
                if st1.st_mtime + 2 >= st2.st_mtime and st1.st_size == st2.st_size:
                    if not self.generator.bld.progress_bar:
                        c1 = Logs.colors.NORMAL
                        c2 = Logs.colors.BLUE
                        Logs.info('%s- install %s%s%s (from %s)', c1, c2, tgt, c1, lbl)
                    return False
        if not self.generator.bld.progress_bar:
            c1 = Logs.colors.NORMAL
            c2 = Logs.colors.BLUE
            Logs.info('%s+ install %s%s%s (from %s)', c1, c2, tgt, c1, lbl)
        try:
            os.chmod(tgt, Utils.O644 | stat.S_IMODE(os.stat(tgt).st_mode))
        except EnvironmentError:
            pass
        try:
            os.remove(tgt)
        except OSError:
            pass
        try:
            self.copy_fun(src, tgt)
        except EnvironmentError as e:
            if not os.path.exists(src):
                Logs.error('File %r does not exist', src)
            elif not os.path.isfile(src):
                Logs.error('Input %r is not a file', src)
            raise Errors.WafError('Could not install the file %r' % tgt, e)

    def fix_perms(self, tgt):
        if not Utils.is_win32:
            user = getattr(self, 'install_user', None) or getattr(self.generator, 'install_user', None)
            group = getattr(self, 'install_group', None) or getattr(self.generator, 'install_group', None)
            if user or group:
                Utils.lchown(tgt, user or -1, group or -1)
        if not os.path.islink(tgt):
            os.chmod(tgt, self.chmod)

    def do_link(self, src, tgt, **kw):
        if os.path.islink(tgt) and os.readlink(tgt) == src:
            if not self.generator.bld.progress_bar:
                c1 = Logs.colors.NORMAL
                c2 = Logs.colors.BLUE
                Logs.info('%s- symlink %s%s%s (to %s)', c1, c2, tgt, c1, src)
        else:
            try:
                os.remove(tgt)
            except OSError:
                pass
            if not self.generator.bld.progress_bar:
                c1 = Logs.colors.NORMAL
                c2 = Logs.colors.BLUE
                Logs.info('%s+ symlink %s%s%s (to %s)', c1, c2, tgt, c1, src)
            os.symlink(src, tgt)
            self.fix_perms(tgt)

    def do_uninstall(self, src, tgt, lbl, **kw):
        if not self.generator.bld.progress_bar:
            c1 = Logs.colors.NORMAL
            c2 = Logs.colors.BLUE
            Logs.info('%s- remove %s%s%s', c1, c2, tgt, c1)
        try:
            os.remove(tgt)
        except OSError as e:
            if e.errno != errno.ENOENT:
                if not getattr(self, 'uninstall_error', None):
                    self.uninstall_error = True
                    Logs.warn('build: some files could not be uninstalled (retry with -vv to list them)')
                if Logs.verbose > 1:
                    Logs.warn('Could not remove %s (error code %r)', e.filename, e.errno)
        self.rm_empty_dirs(tgt)

    def do_unlink(self, src, tgt, **kw):
        try:
            if not self.generator.bld.progress_bar:
                c1 = Logs.colors.NORMAL
                c2 = Logs.colors.BLUE
                Logs.info('%s- remove %s%s%s', c1, c2, tgt, c1)
            os.remove(tgt)
        except OSError:
            pass
        self.rm_empty_dirs(tgt)


class InstallContext(BuildContext):
    '''installs the targets on the system'''
    cmd = 'install'

    def __init__(self, **kw):
        super(InstallContext, self).__init__(**kw)
        self.is_install = INSTALL


class UninstallContext(InstallContext):
    '''removes the targets installed'''
    cmd = 'uninstall'

    def __init__(self, **kw):
        super(UninstallContext, self).__init__(**kw)
        self.is_install = UNINSTALL


class CleanContext(BuildContext):
    '''cleans the project'''
    cmd = 'clean'

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()
        self.recurse([self.run_dir])
        try:
            self.clean()
        finally:
            self.store()

    def clean(self):
        Logs.debug('build: clean called')
        if hasattr(self, 'clean_files'):
            for n in self.clean_files:
                n.delete()
        elif self.bldnode != self.srcnode:
            lst = []
            for env in self.all_envs.values():
                lst.extend(self.root.find_or_declare(f) for f in env[CFG_FILES])
            excluded_dirs = '.lock* *conf_check_*/** config.log %s/*' % CACHE_DIR
            for n in self.bldnode.ant_glob('**/*', excl=excluded_dirs, quiet=True):
                if n in lst:
                    continue
                n.delete()
        self.root.children = {}
        for v in SAVED_ATTRS:
            if v == 'root':
                continue
            setattr(self, v, {})


class ListContext(BuildContext):
    '''lists the targets to execute'''
    cmd = 'list'

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()
        self.recurse([self.run_dir])
        self.pre_build()
        self.timer = Utils.Timer()
        for g in self.groups:
            for tg in g:
                try:
                    f = tg.post
                except AttributeError:
                    pass
                else:
                    f()
        try:
            self.get_tgen_by_name('')
        except Errors.WafError:
            pass
        targets = sorted(self.task_gen_cache_names)
        line_just = max(len(t) for t in targets) if targets else 0
        for target in targets:
            tgen = self.task_gen_cache_names[target]
            descript = getattr(tgen, 'description', '')
            if descript:
                target = target.ljust(line_just)
                descript = ': %s' % descript
            Logs.pprint('GREEN', target, label=descript)


class StepContext(BuildContext):
    '''executes tasks in a step-by-step fashion, for debugging'''
    cmd = 'step'

    def __init__(self, **kw):
        super(StepContext, self).__init__(**kw)
        self.files = Options.options.files

    def compile(self):
        if not self.files:
            Logs.warn('Add a pattern for the debug build, for example "waf step --files=main.c,app"')
            BuildContext.compile(self)
            return
        targets = []
        if self.targets and self.targets != '*':
            targets = self.targets.split(',')
        for g in self.groups:
            for tg in g:
                if targets and tg.name not in targets:
                    continue
                try:
                    f = tg.post
                except AttributeError:
                    pass
                else:
                    f()
            for pat in self.files.split(','):
                matcher = self.get_matcher(pat)
                for tg in g:
                    if isinstance(tg, Task.Task):
                        lst = [tg]
                    else:
                        lst = tg.tasks
                    for tsk in lst:
                        do_exec = False
                        for node in tsk.inputs:
                            if matcher(node, output=False):
                                do_exec = True
                                break
                        for node in tsk.outputs:
                            if matcher(node, output=True):
                                do_exec = True
                                break
                        if do_exec:
                            ret = tsk.run()
                            Logs.info('%s -> exit %r', tsk, ret)

    def get_matcher(self, pat):
        inn = True
        out = True
        if pat.startswith('in:'):
            out = False
            pat = pat.replace('in:', '')
        elif pat.startswith('out:'):
            inn = False
            pat = pat.replace('out:', '')
        anode = self.root.find_node(pat)
        pattern = None
        if not anode:
            if not pat.startswith('^'):
                pat = '^.+?%s' % pat
            if not pat.endswith('$'):
                pat = '%s$' % pat
            pattern = re.compile(pat)

        def match(node, output):
            if output and not out:
                return False
            if not output and not inn:
                return False
            if anode:
                return anode == node
            else:
                return pattern.match(node.abspath())

        return match


class EnvContext(BuildContext):
    fun = cmd = None

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()
        self.recurse([self.run_dir])
