#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

import os, re, sys
from waflib import Utils, Errors, Logs
import waflib.Node
if sys.hexversion > 0x3040000:
    import types

    class imp(object):
        new_module = lambda x: types.ModuleType(x)
else:
    import imp

HEXVERSION = 0x2001400
WAFVERSION = "2.0.20"
WAFREVISION = "668769470956da8c5b60817cb8884cd7d0f87cd4"
WAFNAME = "waf"
ABI = 20
DBFILE = '.wafpickle-%s-%d-%d' % (sys.platform, sys.hexversion, ABI)
APPNAME = 'APPNAME'
VERSION = 'VERSION'
TOP = 'top'
OUT = 'out'
WSCRIPT_FILE = 'wscript'
launch_dir = ''
run_dir = ''
top_dir = ''
out_dir = ''
waf_dir = ''
default_encoding = Utils.console_encoding()
g_module = None
STDOUT = 1
STDERR = -1
BOTH = 0
classes = []


def create_context(cmd_name, *k, **kw):
    for x in classes:
        if x.cmd == cmd_name:
            return x(*k, **kw)
    ctx = Context(*k, **kw)
    ctx.fun = cmd_name
    return ctx


class store_context(type):
    def __init__(cls, name, bases, dct):
        super(store_context, cls).__init__(name, bases, dct)
        name = cls.__name__
        if name in ('ctx', 'Context'):
            return
        try:
            cls.cmd
        except AttributeError:
            raise Errors.WafError('Missing command for the context class %r (cmd)' % name)
        if not getattr(cls, 'fun', None):
            cls.fun = cls.cmd
        classes.insert(0, cls)


ctx = store_context('ctx', (object,), {})


class Context(ctx):
    errors = Errors
    tools = {}

    def __init__(self, **kw):
        try:
            rd = kw['run_dir']
        except KeyError:
            rd = run_dir
        self.node_class = type('Nod3', (waflib.Node.Node,), {})
        self.node_class.__module__ = 'waflib.Node'
        self.node_class.ctx = self
        self.root = self.node_class('', None)
        self.cur_script = None
        self.path = self.root.find_dir(rd)
        self.stack_path = []
        self.exec_dict = {'ctx': self, 'conf': self, 'bld': self, 'opt': self}
        self.logger = None

    def finalize(self):
        try:
            logger = self.logger
        except AttributeError:
            pass
        else:
            Logs.free_logger(logger)
            delattr(self, 'logger')

    def load(self, tool_list, *k, **kw):
        tools = Utils.to_list(tool_list)
        path = Utils.to_list(kw.get('tooldir', ''))
        with_sys_path = kw.get('with_sys_path', True)
        for t in tools:
            module = load_tool(t, path, with_sys_path=with_sys_path)
            fun = getattr(module, kw.get('name', self.fun), None)
            if fun:
                fun(self)

    def execute(self):
        self.recurse([os.path.dirname(g_module.root_path)])

    def pre_recurse(self, node):
        self.stack_path.append(self.cur_script)
        self.cur_script = node
        self.path = node.parent

    def post_recurse(self, node):
        self.cur_script = self.stack_path.pop()
        if self.cur_script:
            self.path = self.cur_script.parent

    def recurse(self, dirs, name=None, mandatory=True, once=True, encoding=None):
        try:
            cache = self.recurse_cache
        except AttributeError:
            cache = self.recurse_cache = {}
        for d in Utils.to_list(dirs):
            if not os.path.isabs(d):
                d = os.path.join(self.path.abspath(), d)
            WSCRIPT = os.path.join(d, WSCRIPT_FILE)
            WSCRIPT_FUN = WSCRIPT + '_' + (name or self.fun)
            node = self.root.find_node(WSCRIPT_FUN)
            if node and (not once or node not in cache):
                cache[node] = True
                self.pre_recurse(node)
                try:
                    function_code = node.read('r', encoding)
                    exec(compile(function_code, node.abspath(), 'exec'), self.exec_dict)
                finally:
                    self.post_recurse(node)
            elif not node:
                node = self.root.find_node(WSCRIPT)
                tup = (node, name or self.fun)
                if node and (not once or tup not in cache):
                    cache[tup] = True
                    self.pre_recurse(node)
                    try:
                        wscript_module = load_module(node.abspath(), encoding=encoding)
                        user_function = getattr(wscript_module, (name or self.fun), None)
                        if not user_function:
                            if not mandatory:
                                continue
                            raise Errors.WafError('No function %r defined in %s' % (name or self.fun, node.abspath()))
                        user_function(self)
                    finally:
                        self.post_recurse(node)
                elif not node:
                    if not mandatory:
                        continue
                    try:
                        os.listdir(d)
                    except OSError:
                        raise Errors.WafError('Cannot read the folder %r' % d)
                    raise Errors.WafError('No wscript file in directory %s' % d)

    def log_command(self, cmd, kw):
        if Logs.verbose:
            fmt = os.environ.get('WAF_CMD_FORMAT')
            if fmt == 'string':
                if not isinstance(cmd, str):
                    cmd = Utils.shell_escape(cmd)
            Logs.debug('runner: %r', cmd)
            Logs.debug('runner_env: kw=%s', kw)

    def exec_command(self, cmd, **kw):
        subprocess = Utils.subprocess
        kw['shell'] = isinstance(cmd, str)
        self.log_command(cmd, kw)
        if self.logger:
            self.logger.info(cmd)
        if 'stdout' not in kw:
            kw['stdout'] = subprocess.PIPE
        if 'stderr' not in kw:
            kw['stderr'] = subprocess.PIPE
        if Logs.verbose and not kw['shell'] and not Utils.check_exe(cmd[0]):
            raise Errors.WafError('Program %s not found!' % cmd[0])
        cargs = {}
        if 'timeout' in kw:
            if sys.hexversion >= 0x3030000:
                cargs['timeout'] = kw['timeout']
                if not 'start_new_session' in kw:
                    kw['start_new_session'] = True
            del kw['timeout']
        if 'input' in kw:
            if kw['input']:
                cargs['input'] = kw['input']
                kw['stdin'] = subprocess.PIPE
            del kw['input']
        if 'cwd' in kw:
            if not isinstance(kw['cwd'], str):
                kw['cwd'] = kw['cwd'].abspath()
        encoding = kw.pop('decode_as', default_encoding)
        try:
            ret, out, err = Utils.run_process(cmd, kw, cargs)
        except Exception as e:
            raise Errors.WafError('Execution failure: %s' % str(e), ex=e)
        if out:
            if not isinstance(out, str):
                out = out.decode(encoding, errors='replace')
            if self.logger:
                self.logger.debug('out: %s', out)
            else:
                Logs.info(out, extra={'stream': sys.stdout, 'c1': ''})
        if err:
            if not isinstance(err, str):
                err = err.decode(encoding, errors='replace')
            if self.logger:
                self.logger.error('err: %s' % err)
            else:
                Logs.info(err, extra={'stream': sys.stderr, 'c1': ''})
        return ret

    def cmd_and_log(self, cmd, **kw):
        subprocess = Utils.subprocess
        kw['shell'] = isinstance(cmd, str)
        self.log_command(cmd, kw)
        quiet = kw.pop('quiet', None)
        to_ret = kw.pop('output', STDOUT)
        if Logs.verbose and not kw['shell'] and not Utils.check_exe(cmd[0]):
            raise Errors.WafError('Program %r not found!' % cmd[0])
        kw['stdout'] = kw['stderr'] = subprocess.PIPE
        if quiet is None:
            self.to_log(cmd)
        cargs = {}
        if 'timeout' in kw:
            if sys.hexversion >= 0x3030000:
                cargs['timeout'] = kw['timeout']
                if not 'start_new_session' in kw:
                    kw['start_new_session'] = True
            del kw['timeout']
        if 'input' in kw:
            if kw['input']:
                cargs['input'] = kw['input']
                kw['stdin'] = subprocess.PIPE
            del kw['input']
        if 'cwd' in kw:
            if not isinstance(kw['cwd'], str):
                kw['cwd'] = kw['cwd'].abspath()
        encoding = kw.pop('decode_as', default_encoding)
        try:
            ret, out, err = Utils.run_process(cmd, kw, cargs)
        except Exception as e:
            raise Errors.WafError('Execution failure: %s' % str(e), ex=e)
        if not isinstance(out, str):
            out = out.decode(encoding, errors='replace')
        if not isinstance(err, str):
            err = err.decode(encoding, errors='replace')
        if out and quiet != STDOUT and quiet != BOTH:
            self.to_log('out: %s' % out)
        if err and quiet != STDERR and quiet != BOTH:
            self.to_log('err: %s' % err)
        if ret:
            e = Errors.WafError('Command %r returned %r' % (cmd, ret))
            e.returncode = ret
            e.stderr = err
            e.stdout = out
            raise e
        if to_ret == BOTH:
            return (out, err)
        elif to_ret == STDERR:
            return err
        return out

    def fatal(self, msg, ex=None):
        if self.logger:
            self.logger.info('from %s: %s' % (self.path.abspath(), msg))
        try:
            logfile = self.logger.handlers[0].baseFilename
        except AttributeError:
            pass
        else:
            if os.environ.get('WAF_PRINT_FAILURE_LOG'):
                msg = 'Log from (%s):\n%s\n' % (logfile, Utils.readf(logfile))
            else:
                msg = '%s\n(complete log in %s)' % (msg, logfile)
        raise self.errors.ConfigurationError(msg, ex=ex)

    def to_log(self, msg):
        if not msg:
            return
        if self.logger:
            self.logger.info(msg)
        else:
            sys.stderr.write(str(msg))
            sys.stderr.flush()

    def msg(self, *k, **kw):
        try:
            msg = kw['msg']
        except KeyError:
            msg = k[0]
        self.start_msg(msg, **kw)
        try:
            result = kw['result']
        except KeyError:
            result = k[1]
        color = kw.get('color')
        if not isinstance(color, str):
            color = result and 'GREEN' or 'YELLOW'
        self.end_msg(result, color, **kw)

    def start_msg(self, *k, **kw):
        if kw.get('quiet'):
            return
        msg = kw.get('msg') or k[0]
        try:
            if self.in_msg:
                self.in_msg += 1
                return
        except AttributeError:
            self.in_msg = 0
        self.in_msg += 1
        try:
            self.line_just = max(self.line_just, len(msg))
        except AttributeError:
            self.line_just = max(40, len(msg))
        for x in (self.line_just * '-', msg):
            self.to_log(x)
        Logs.pprint('NORMAL', "%s :" % msg.ljust(self.line_just), sep='')

    def end_msg(self, *k, **kw):
        if kw.get('quiet'):
            return
        self.in_msg -= 1
        if self.in_msg:
            return
        result = kw.get('result') or k[0]
        defcolor = 'GREEN'
        if result is True:
            msg = 'ok'
        elif not result:
            msg = 'not found'
            defcolor = 'YELLOW'
        else:
            msg = str(result)
        self.to_log(msg)
        try:
            color = kw['color']
        except KeyError:
            if len(k) > 1 and k[1] in Logs.colors_lst:
                color = k[1]
            else:
                color = defcolor
        Logs.pprint(color, msg)

    def load_special_tools(self, var, ban=[]):
        if os.path.isdir(waf_dir):
            lst = self.root.find_node(waf_dir).find_node('waflib/extras').ant_glob(var)
            for x in lst:
                if not x.name in ban:
                    load_tool(x.name.replace('.py', ''))
        else:
            from zipfile import PyZipFile
            waflibs = PyZipFile(waf_dir)
            lst = waflibs.namelist()
            for x in lst:
                if not re.match('waflib/extras/%s' % var.replace('*', '.*'), var):
                    continue
                f = os.path.basename(x)
                doban = False
                for b in ban:
                    r = b.replace('*', '.*')
                    if re.match(r, f):
                        doban = True
                if not doban:
                    f = f.replace('.py', '')
                    load_tool(f)


cache_modules = {}


def load_module(path, encoding=None):
    try:
        return cache_modules[path]
    except KeyError:
        pass
    module = imp.new_module(WSCRIPT_FILE)
    try:
        code = Utils.readf(path, m='r', encoding=encoding)
    except EnvironmentError:
        raise Errors.WafError('Could not read the file %r' % path)
    module_dir = os.path.dirname(path)
    sys.path.insert(0, module_dir)
    try:
        exec(compile(code, path, 'exec'), module.__dict__)
    finally:
        sys.path.remove(module_dir)
    cache_modules[path] = module
    return module


def load_tool(tool, tooldir=None, ctx=None, with_sys_path=True):
    if tool == 'java':
        tool = 'javaw'
    else:
        tool = tool.replace('++', 'xx')
    if not with_sys_path:
        back_path = sys.path
        sys.path = []
    try:
        if tooldir:
            assert isinstance(tooldir, list)
            sys.path = tooldir + sys.path
            try:
                __import__(tool)
            except ImportError as e:
                e.waf_sys_path = list(sys.path)
                raise
            finally:
                for d in tooldir:
                    sys.path.remove(d)
            ret = sys.modules[tool]
            Context.tools[tool] = ret
            return ret
        else:
            if not with_sys_path:
                sys.path.insert(0, waf_dir)
            try:
                for x in ('waflib.Tools.%s', 'waflib.extras.%s', 'waflib.%s', '%s'):
                    try:
                        __import__(x % tool)
                        break
                    except ImportError:
                        x = None
                else:
                    __import__(tool)
            except ImportError as e:
                e.waf_sys_path = list(sys.path)
                raise
            finally:
                if not with_sys_path:
                    sys.path.remove(waf_dir)
            ret = sys.modules[x % tool]
            Context.tools[tool] = ret
            return ret
    finally:
        if not with_sys_path:
            sys.path += back_path
