#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

from __future__ import with_statement
import os, re, shlex
from waflib import Build, Utils, Task, Options, Logs, Errors, Runner
from waflib.TaskGen import after_method, feature
from waflib.Configure import conf

WAF_CONFIG_H = 'config.h'
DEFKEYS = 'define_key'
INCKEYS = 'include_key'
SNIP_EMPTY_PROGRAM = '''
int main(int argc, char **argv) {
	(void)argc; (void)argv;
	return 0;
}
'''
MACRO_TO_DESTOS = {
    '__linux__': 'linux',
    '__GNU__': 'gnu',
    '__FreeBSD__': 'freebsd',
    '__NetBSD__': 'netbsd',
    '__OpenBSD__': 'openbsd',
    '__sun': 'sunos',
    '__hpux': 'hpux',
    '__sgi': 'irix',
    '_AIX': 'aix',
    '__CYGWIN__': 'cygwin',
    '__MSYS__': 'cygwin',
    '_UWIN': 'uwin',
    '_WIN64': 'win32',
    '_WIN32': 'win32',
    '__ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__': 'darwin',
    '__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__': 'darwin',
    '__QNX__': 'qnx',
    '__native_client__': 'nacl'
}
MACRO_TO_DEST_CPU = {
    '__x86_64__': 'x86_64',
    '__amd64__': 'x86_64',
    '__i386__': 'x86',
    '__ia64__': 'ia',
    '__mips__': 'mips',
    '__sparc__': 'sparc',
    '__alpha__': 'alpha',
    '__aarch64__': 'aarch64',
    '__thumb__': 'thumb',
    '__arm__': 'arm',
    '__hppa__': 'hppa',
    '__powerpc__': 'powerpc',
    '__ppc__': 'powerpc',
    '__convex__': 'convex',
    '__m68k__': 'm68k',
    '__s390x__': 's390x',
    '__s390__': 's390',
    '__sh__': 'sh',
    '__xtensa__': 'xtensa',
    '__riscv': 'riscv',
}


@conf
def parse_flags(self, line, uselib_store, env=None, force_static=False, posix=None):
    assert (isinstance(line, str))
    env = env or self.env
    if posix is None:
        posix = True
        if '\\' in line:
            posix = ('\\ ' in line) or ('\\\\' in line)
    lex = shlex.shlex(line, posix=posix)
    lex.whitespace_split = True
    lex.commenters = ''
    lst = list(lex)
    so_re = re.compile(r"\.so(?:\.[0-9]+)*$")
    uselib = uselib_store

    def app(var, val):
        env.append_value('%s_%s' % (var, uselib), val)

    def appu(var, val):
        env.append_unique('%s_%s' % (var, uselib), val)

    static = False
    while lst:
        x = lst.pop(0)
        st = x[:2]
        ot = x[2:]
        if st == '-I' or st == '/I':
            if not ot:
                ot = lst.pop(0)
            appu('INCLUDES', ot)
        elif st == '-i':
            tmp = [x, lst.pop(0)]
            app('CFLAGS', tmp)
            app('CXXFLAGS', tmp)
        elif st == '-D' or (env.CXX_NAME == 'msvc' and st == '/D'):
            if not ot:
                ot = lst.pop(0)
            app('DEFINES', ot)
        elif st == '-l':
            if not ot:
                ot = lst.pop(0)
            prefix = 'STLIB' if (force_static or static) else 'LIB'
            app(prefix, ot)
        elif st == '-L':
            if not ot:
                ot = lst.pop(0)
            prefix = 'STLIBPATH' if (force_static or static) else 'LIBPATH'
            appu(prefix, ot)
        elif x.startswith('/LIBPATH:'):
            prefix = 'STLIBPATH' if (force_static or static) else 'LIBPATH'
            appu(prefix, x.replace('/LIBPATH:', ''))
        elif x.startswith('-std='):
            prefix = 'CXXFLAGS' if '++' in x else 'CFLAGS'
            app(prefix, x)
        elif x.startswith('+') or x in ('-pthread', '-fPIC', '-fpic', '-fPIE', '-fpie', '-flto', '-fno-lto'):
            app('CFLAGS', x)
            app('CXXFLAGS', x)
            app('LINKFLAGS', x)
        elif x == '-framework':
            appu('FRAMEWORK', lst.pop(0))
        elif x.startswith('-F'):
            appu('FRAMEWORKPATH', x[2:])
        elif x == '-Wl,-rpath' or x == '-Wl,-R':
            app('RPATH', lst.pop(0).lstrip('-Wl,'))
        elif x.startswith('-Wl,-R,'):
            app('RPATH', x[7:])
        elif x.startswith('-Wl,-R'):
            app('RPATH', x[6:])
        elif x.startswith('-Wl,-rpath,'):
            app('RPATH', x[11:])
        elif x == '-Wl,-Bstatic' or x == '-Bstatic':
            static = True
        elif x == '-Wl,-Bdynamic' or x == '-Bdynamic':
            static = False
        elif x.startswith('-Wl') or x in ('-rdynamic', '-pie'):
            app('LINKFLAGS', x)
        elif x.startswith(('-m', '-f', '-dynamic', '-O', '-g')):
            app('CFLAGS', x)
            app('CXXFLAGS', x)
        elif x.startswith('-bundle'):
            app('LINKFLAGS', x)
        elif x.startswith(('-undefined', '-Xlinker')):
            arg = lst.pop(0)
            app('LINKFLAGS', [x, arg])
        elif x.startswith(('-arch', '-isysroot')):
            tmp = [x, lst.pop(0)]
            app('CFLAGS', tmp)
            app('CXXFLAGS', tmp)
            app('LINKFLAGS', tmp)
        elif x.endswith(('.a', '.dylib', '.lib')) or so_re.search(x):
            appu('LINKFLAGS', x)
        else:
            self.to_log('Unhandled flag %r' % x)


@conf
def validate_cfg(self, kw):
    if not 'path' in kw:
        if not self.env.PKGCONFIG:
            self.find_program('pkg-config', var='PKGCONFIG')
        kw['path'] = self.env.PKGCONFIG
    s = ('atleast_pkgconfig_version' in kw) + ('modversion' in kw) + ('package' in kw)
    if s != 1:
        raise ValueError('exactly one of atleast_pkgconfig_version, modversion and package must be set')
    if not 'msg' in kw:
        if 'atleast_pkgconfig_version' in kw:
            kw['msg'] = 'Checking for pkg-config version >= %r' % kw['atleast_pkgconfig_version']
        elif 'modversion' in kw:
            kw['msg'] = 'Checking for %r version' % kw['modversion']
        else:
            kw['msg'] = 'Checking for %r' % (kw['package'])
    if not 'okmsg' in kw and not 'modversion' in kw:
        kw['okmsg'] = 'yes'
    if not 'errmsg' in kw:
        kw['errmsg'] = 'not found'
    if 'atleast_pkgconfig_version' in kw:
        pass
    elif 'modversion' in kw:
        if not 'uselib_store' in kw:
            kw['uselib_store'] = kw['modversion']
        if not 'define_name' in kw:
            kw['define_name'] = '%s_VERSION' % Utils.quote_define_name(kw['uselib_store'])
    else:
        if not 'uselib_store' in kw:
            kw['uselib_store'] = Utils.to_list(kw['package'])[0].upper()
        if not 'define_name' in kw:
            kw['define_name'] = self.have_define(kw['uselib_store'])


@conf
def exec_cfg(self, kw):
    path = Utils.to_list(kw['path'])
    env = self.env.env or None
    if kw.get('pkg_config_path'):
        if not env:
            env = dict(self.environ)
        env['PKG_CONFIG_PATH'] = kw['pkg_config_path']

    def define_it():
        define_name = kw['define_name']
        if kw.get('global_define', 1):
            self.define(define_name, 1, False)
        else:
            self.env.append_unique('DEFINES_%s' % kw['uselib_store'], "%s=1" % define_name)
        if kw.get('add_have_to_env', 1):
            self.env[define_name] = 1

    if 'atleast_pkgconfig_version' in kw:
        cmd = path + ['--atleast-pkgconfig-version=%s' % kw['atleast_pkgconfig_version']]
        self.cmd_and_log(cmd, env=env)
        return
    if 'modversion' in kw:
        version = self.cmd_and_log(path + ['--modversion', kw['modversion']], env=env).strip()
        if not 'okmsg' in kw:
            kw['okmsg'] = version
        self.define(kw['define_name'], version)
        return version
    lst = [] + path
    defi = kw.get('define_variable')
    if not defi:
        defi = self.env.PKG_CONFIG_DEFINES or {}
    for key, val in defi.items():
        lst.append('--define-variable=%s=%s' % (key, val))
    static = kw.get('force_static', False)
    if 'args' in kw:
        args = Utils.to_list(kw['args'])
        if '--static' in args or '--static-libs' in args:
            static = True
        lst += args
    lst.extend(Utils.to_list(kw['package']))
    if 'variables' in kw:
        v_env = kw.get('env', self.env)
        vars = Utils.to_list(kw['variables'])
        for v in vars:
            val = self.cmd_and_log(lst + ['--variable=' + v], env=env).strip()
            var = '%s_%s' % (kw['uselib_store'], v)
            v_env[var] = val
        return
    ret = self.cmd_and_log(lst, env=env)
    define_it()
    self.parse_flags(ret, kw['uselib_store'], kw.get('env', self.env), force_static=static, posix=kw.get('posix'))
    return ret


@conf
def check_cfg(self, *k, **kw):
    self.validate_cfg(kw)
    if 'msg' in kw:
        self.start_msg(kw['msg'], **kw)
    ret = None
    try:
        ret = self.exec_cfg(kw)
    except self.errors.WafError as e:
        if 'errmsg' in kw:
            self.end_msg(kw['errmsg'], 'YELLOW', **kw)
        if Logs.verbose > 1:
            self.to_log('Command failure: %s' % e)
        self.fatal('The configuration failed')
    else:
        if not ret:
            ret = True
        kw['success'] = ret
        if 'okmsg' in kw:
            self.end_msg(self.ret_msg(kw['okmsg'], kw), **kw)
    return ret


def build_fun(bld):
    if bld.kw['compile_filename']:
        node = bld.srcnode.make_node(bld.kw['compile_filename'])
        node.write(bld.kw['code'])
    o = bld(features=bld.kw['features'], source=bld.kw['compile_filename'], target='testprog')
    for k, v in bld.kw.items():
        setattr(o, k, v)
    if not bld.kw.get('quiet'):
        bld.conf.to_log("==>\n%s\n<==" % bld.kw['code'])


@conf
def validate_c(self, kw):
    for x in ('type_name', 'field_name', 'function_name'):
        if x in kw:
            Logs.warn('Invalid argument %r in test' % x)
    if not 'build_fun' in kw:
        kw['build_fun'] = build_fun
    if not 'env' in kw:
        kw['env'] = self.env.derive()
    env = kw['env']
    if not 'compiler' in kw and not 'features' in kw:
        kw['compiler'] = 'c'
        if env.CXX_NAME and Task.classes.get('cxx'):
            kw['compiler'] = 'cxx'
            if not self.env.CXX:
                self.fatal('a c++ compiler is required')
        else:
            if not self.env.CC:
                self.fatal('a c compiler is required')
    if not 'compile_mode' in kw:
        kw['compile_mode'] = 'c'
        if 'cxx' in Utils.to_list(kw.get('features', [])) or kw.get('compiler') == 'cxx':
            kw['compile_mode'] = 'cxx'
    if not 'type' in kw:
        kw['type'] = 'cprogram'
    if not 'features' in kw:
        if not 'header_name' in kw or kw.get('link_header_test', True):
            kw['features'] = [kw['compile_mode'], kw['type']]
        else:
            kw['features'] = [kw['compile_mode']]
    else:
        kw['features'] = Utils.to_list(kw['features'])
    if not 'compile_filename' in kw:
        kw['compile_filename'] = 'test.c' + ((kw['compile_mode'] == 'cxx') and 'pp' or '')

    def to_header(dct):
        if 'header_name' in dct:
            dct = Utils.to_list(dct['header_name'])
            return ''.join(['#include <%s>\n' % x for x in dct])
        return ''

    if 'framework_name' in kw:
        fwkname = kw['framework_name']
        if not 'uselib_store' in kw:
            kw['uselib_store'] = fwkname.upper()
        if not kw.get('no_header'):
            fwk = '%s/%s.h' % (fwkname, fwkname)
            if kw.get('remove_dot_h'):
                fwk = fwk[:-2]
            val = kw.get('header_name', [])
            kw['header_name'] = Utils.to_list(val) + [fwk]
        kw['msg'] = 'Checking for framework %s' % fwkname
        kw['framework'] = fwkname
    elif 'header_name' in kw:
        if not 'msg' in kw:
            kw['msg'] = 'Checking for header %s' % kw['header_name']
        l = Utils.to_list(kw['header_name'])
        assert len(l), 'list of headers in header_name is empty'
        kw['code'] = to_header(kw) + SNIP_EMPTY_PROGRAM
        if not 'uselib_store' in kw:
            kw['uselib_store'] = l[0].upper()
        if not 'define_name' in kw:
            kw['define_name'] = self.have_define(l[0])
    if 'lib' in kw:
        if not 'msg' in kw:
            kw['msg'] = 'Checking for library %s' % kw['lib']
        if not 'uselib_store' in kw:
            kw['uselib_store'] = kw['lib'].upper()
    if 'stlib' in kw:
        if not 'msg' in kw:
            kw['msg'] = 'Checking for static library %s' % kw['stlib']
        if not 'uselib_store' in kw:
            kw['uselib_store'] = kw['stlib'].upper()
    if 'fragment' in kw:
        kw['code'] = kw['fragment']
        if not 'msg' in kw:
            kw['msg'] = 'Checking for code snippet'
        if not 'errmsg' in kw:
            kw['errmsg'] = 'no'
    for (flagsname, flagstype) in (('cxxflags', 'compiler'), ('cflags', 'compiler'), ('linkflags', 'linker')):
        if flagsname in kw:
            if not 'msg' in kw:
                kw['msg'] = 'Checking for %s flags %s' % (flagstype, kw[flagsname])
            if not 'errmsg' in kw:
                kw['errmsg'] = 'no'
    if not 'execute' in kw:
        kw['execute'] = False
    if kw['execute']:
        kw['features'].append('test_exec')
        kw['chmod'] = Utils.O755
    if not 'errmsg' in kw:
        kw['errmsg'] = 'not found'
    if not 'okmsg' in kw:
        kw['okmsg'] = 'yes'
    if not 'code' in kw:
        kw['code'] = SNIP_EMPTY_PROGRAM
    if self.env[INCKEYS]:
        kw['code'] = '\n'.join(['#include <%s>' % x for x in self.env[INCKEYS]]) + '\n' + kw['code']
    if kw.get('merge_config_header') or env.merge_config_header:
        kw['code'] = '%s\n\n%s' % (self.get_config_header(), kw['code'])
        env.DEFINES = []
    if not kw.get('success'):
        kw['success'] = None
    if 'define_name' in kw:
        self.undefine(kw['define_name'])
    if not 'msg' in kw:
        self.fatal('missing "msg" in conf.check(...)')


@conf
def post_check(self, *k, **kw):
    is_success = 0
    if kw['execute']:
        if kw['success'] is not None:
            if kw.get('define_ret'):
                is_success = kw['success']
            else:
                is_success = (kw['success'] == 0)
    else:
        is_success = (kw['success'] == 0)
    if kw.get('define_name'):
        comment = kw.get('comment', '')
        define_name = kw['define_name']
        if kw['execute'] and kw.get('define_ret') and isinstance(is_success, str):
            if kw.get('global_define', 1):
                self.define(define_name, is_success, quote=kw.get('quote', 1), comment=comment)
            else:
                if kw.get('quote', 1):
                    succ = '"%s"' % is_success
                else:
                    succ = int(is_success)
                val = '%s=%s' % (define_name, succ)
                var = 'DEFINES_%s' % kw['uselib_store']
                self.env.append_value(var, val)
        else:
            if kw.get('global_define', 1):
                self.define_cond(define_name, is_success, comment=comment)
            else:
                var = 'DEFINES_%s' % kw['uselib_store']
                self.env.append_value(var, '%s=%s' % (define_name, int(is_success)))
        if kw.get('add_have_to_env', 1):
            if kw.get('uselib_store'):
                self.env[self.have_define(kw['uselib_store'])] = 1
            elif kw['execute'] and kw.get('define_ret'):
                self.env[define_name] = is_success
            else:
                self.env[define_name] = int(is_success)
    if 'header_name' in kw:
        if kw.get('auto_add_header_name'):
            self.env.append_value(INCKEYS, Utils.to_list(kw['header_name']))
    if is_success and 'uselib_store' in kw:
        from waflib.Tools import ccroot
        _vars = set()
        for x in kw['features']:
            if x in ccroot.USELIB_VARS:
                _vars |= ccroot.USELIB_VARS[x]
        for k in _vars:
            x = k.lower()
            if x in kw:
                self.env.append_value(k + '_' + kw['uselib_store'], kw[x])
    return is_success


@conf
def check(self, *k, **kw):
    self.validate_c(kw)
    self.start_msg(kw['msg'], **kw)
    ret = None
    try:
        ret = self.run_build(*k, **kw)
    except self.errors.ConfigurationError:
        self.end_msg(kw['errmsg'], 'YELLOW', **kw)
        if Logs.verbose > 1:
            raise
        else:
            self.fatal('The configuration failed')
    else:
        kw['success'] = ret
    ret = self.post_check(*k, **kw)
    if not ret:
        self.end_msg(kw['errmsg'], 'YELLOW', **kw)
        self.fatal('The configuration failed %r' % ret)
    else:
        self.end_msg(self.ret_msg(kw['okmsg'], kw), **kw)
    return ret


class test_exec(Task.Task):
    color = 'PINK'

    def run(self):
        cmd = [self.inputs[0].abspath()] + getattr(self.generator, 'test_args', [])
        if getattr(self.generator, 'rpath', None):
            if getattr(self.generator, 'define_ret', False):
                self.generator.bld.retval = self.generator.bld.cmd_and_log(cmd)
            else:
                self.generator.bld.retval = self.generator.bld.exec_command(cmd)
        else:
            env = self.env.env or {}
            env.update(dict(os.environ))
            for var in ('LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'PATH'):
                env[var] = self.inputs[0].parent.abspath() + os.path.pathsep + env.get(var, '')
            if getattr(self.generator, 'define_ret', False):
                self.generator.bld.retval = self.generator.bld.cmd_and_log(cmd, env=env)
            else:
                self.generator.bld.retval = self.generator.bld.exec_command(cmd, env=env)


@feature('test_exec')
@after_method('apply_link')
def test_exec_fun(self):
    self.create_task('test_exec', self.link_task.outputs[0])


@conf
def check_cxx(self, *k, **kw):
    kw['compiler'] = 'cxx'
    return self.check(*k, **kw)


@conf
def check_cc(self, *k, **kw):
    kw['compiler'] = 'c'
    return self.check(*k, **kw)


@conf
def set_define_comment(self, key, comment):
    coms = self.env.DEFINE_COMMENTS
    if not coms:
        coms = self.env.DEFINE_COMMENTS = {}
    coms[key] = comment or ''


@conf
def get_define_comment(self, key):
    coms = self.env.DEFINE_COMMENTS or {}
    return coms.get(key, '')


@conf
def define(self, key, val, quote=True, comment=''):
    assert isinstance(key, str)
    if not key:
        return
    if val is True:
        val = 1
    elif val in (False, None):
        val = 0
    if isinstance(val, int) or isinstance(val, float):
        s = '%s=%s'
    else:
        s = quote and '%s="%s"' or '%s=%s'
    app = s % (key, str(val))
    ban = key + '='
    lst = self.env.DEFINES
    for x in lst:
        if x.startswith(ban):
            lst[lst.index(x)] = app
            break
    else:
        self.env.append_value('DEFINES', app)
    self.env.append_unique(DEFKEYS, key)
    self.set_define_comment(key, comment)


@conf
def undefine(self, key, comment=''):
    assert isinstance(key, str)
    if not key:
        return
    ban = key + '='
    lst = [x for x in self.env.DEFINES if not x.startswith(ban)]
    self.env.DEFINES = lst
    self.env.append_unique(DEFKEYS, key)
    self.set_define_comment(key, comment)


@conf
def define_cond(self, key, val, comment=''):
    assert isinstance(key, str)
    if not key:
        return
    if val:
        self.define(key, 1, comment=comment)
    else:
        self.undefine(key, comment=comment)


@conf
def is_defined(self, key):
    assert key and isinstance(key, str)
    ban = key + '='
    for x in self.env.DEFINES:
        if x.startswith(ban):
            return True
    return False


@conf
def get_define(self, key):
    assert key and isinstance(key, str)
    ban = key + '='
    for x in self.env.DEFINES:
        if x.startswith(ban):
            return x[len(ban):]
    return None


@conf
def have_define(self, key):
    return (self.env.HAVE_PAT or 'HAVE_%s') % Utils.quote_define_name(key)


@conf
def write_config_header(
    self, configfile='', guard='', top=False, defines=True, headers=False, remove=True, define_prefix=''
):
    if not configfile:
        configfile = WAF_CONFIG_H
    waf_guard = guard or 'W_%s_WAF' % Utils.quote_define_name(configfile)
    node = top and self.bldnode or self.path.get_bld()
    node = node.make_node(configfile)
    node.parent.mkdir()
    lst = ['/* WARNING! All changes made to this file will be lost! */\n']
    lst.append('#ifndef %s\n#define %s\n' % (waf_guard, waf_guard))
    lst.append(self.get_config_header(defines, headers, define_prefix=define_prefix))
    lst.append('\n#endif /* %s */\n' % waf_guard)
    node.write('\n'.join(lst))
    self.env.append_unique(Build.CFG_FILES, [node.abspath()])
    if remove:
        for key in self.env[DEFKEYS]:
            self.undefine(key)
        self.env[DEFKEYS] = []


@conf
def get_config_header(self, defines=True, headers=False, define_prefix=''):
    lst = []
    if self.env.WAF_CONFIG_H_PRELUDE:
        lst.append(self.env.WAF_CONFIG_H_PRELUDE)
    if headers:
        for x in self.env[INCKEYS]:
            lst.append('#include <%s>' % x)
    if defines:
        tbl = {}
        for k in self.env.DEFINES:
            a, _, b = k.partition('=')
            tbl[a] = b
        for k in self.env[DEFKEYS]:
            caption = self.get_define_comment(k)
            if caption:
                caption = ' /* %s */' % caption
            try:
                txt = '#define %s%s %s%s' % (define_prefix, k, tbl[k], caption)
            except KeyError:
                txt = '/* #undef %s%s */%s' % (define_prefix, k, caption)
            lst.append(txt)
    return "\n".join(lst)


@conf
def cc_add_flags(conf):
    conf.add_os_flags('CPPFLAGS', dup=False)
    conf.add_os_flags('CFLAGS', dup=False)


@conf
def cxx_add_flags(conf):
    conf.add_os_flags('CPPFLAGS', dup=False)
    conf.add_os_flags('CXXFLAGS', dup=False)


@conf
def link_add_flags(conf):
    conf.add_os_flags('LINKFLAGS', dup=False)
    conf.add_os_flags('LDFLAGS', dup=False)


@conf
def cc_load_tools(conf):
    if not conf.env.DEST_OS:
        conf.env.DEST_OS = Utils.unversioned_sys_platform()
    conf.load('c')


@conf
def cxx_load_tools(conf):
    if not conf.env.DEST_OS:
        conf.env.DEST_OS = Utils.unversioned_sys_platform()
    conf.load('cxx')


@conf
def get_cc_version(conf, cc, gcc=False, icc=False, clang=False):
    cmd = cc + ['-dM', '-E', '-']
    env = conf.env.env or None
    try:
        out, err = conf.cmd_and_log(cmd, output=0, input='\n'.encode(), env=env)
    except Errors.WafError:
        conf.fatal('Could not determine the compiler version %r' % cmd)
    if gcc:
        if out.find('__INTEL_COMPILER') >= 0:
            conf.fatal('The intel compiler pretends to be gcc')
        if out.find('__GNUC__') < 0 and out.find('__clang__') < 0:
            conf.fatal('Could not determine the compiler type')
    if icc and out.find('__INTEL_COMPILER') < 0:
        conf.fatal('Not icc/icpc')
    if clang and out.find('__clang__') < 0:
        conf.fatal('Not clang/clang++')
    if not clang and out.find('__clang__') >= 0:
        conf.fatal('Could not find gcc/g++ (only Clang), if renamed try eg: CC=gcc48 CXX=g++48 waf configure')
    k = {}
    if icc or gcc or clang:
        out = out.splitlines()
        for line in out:
            lst = shlex.split(line)
            if len(lst) > 2:
                key = lst[1]
                val = lst[2]
                k[key] = val

        def isD(var):
            return var in k

        if not conf.env.DEST_OS:
            conf.env.DEST_OS = ''
        for i in MACRO_TO_DESTOS:
            if isD(i):
                conf.env.DEST_OS = MACRO_TO_DESTOS[i]
                break
        else:
            if isD('__APPLE__') and isD('__MACH__'):
                conf.env.DEST_OS = 'darwin'
            elif isD('__unix__'):
                conf.env.DEST_OS = 'generic'
        if isD('__ELF__'):
            conf.env.DEST_BINFMT = 'elf'
        elif isD('__WINNT__') or isD('__CYGWIN__') or isD('_WIN32'):
            conf.env.DEST_BINFMT = 'pe'
            if not conf.env.IMPLIBDIR:
                conf.env.IMPLIBDIR = conf.env.LIBDIR
            conf.env.LIBDIR = conf.env.BINDIR
        elif isD('__APPLE__'):
            conf.env.DEST_BINFMT = 'mac-o'
        if not conf.env.DEST_BINFMT:
            conf.env.DEST_BINFMT = Utils.destos_to_binfmt(conf.env.DEST_OS)
        for i in MACRO_TO_DEST_CPU:
            if isD(i):
                conf.env.DEST_CPU = MACRO_TO_DEST_CPU[i]
                break
        Logs.debug(
            'ccroot: dest platform: ' + ' '.join([conf.env[x] or '?' for x in ('DEST_OS', 'DEST_BINFMT', 'DEST_CPU')])
        )
        if icc:
            ver = k['__INTEL_COMPILER']
            conf.env.CC_VERSION = (ver[:-2], ver[-2], ver[-1])
        else:
            if isD('__clang__') and isD('__clang_major__'):
                conf.env.CC_VERSION = (k['__clang_major__'], k['__clang_minor__'], k['__clang_patchlevel__'])
            else:
                conf.env.CC_VERSION = (k['__GNUC__'], k['__GNUC_MINOR__'], k.get('__GNUC_PATCHLEVEL__', '0'))
    return k


@conf
def get_xlc_version(conf, cc):
    cmd = cc + ['-qversion']
    try:
        out, err = conf.cmd_and_log(cmd, output=0)
    except Errors.WafError:
        conf.fatal('Could not find xlc %r' % cmd)
    for v in (r"IBM XL C/C\+\+.* V(?P<major>\d*)\.(?P<minor>\d*)",):
        version_re = re.compile(v, re.I).search
        match = version_re(out or err)
        if match:
            k = match.groupdict()
            conf.env.CC_VERSION = (k['major'], k['minor'])
            break
    else:
        conf.fatal('Could not determine the XLC version.')


@conf
def get_suncc_version(conf, cc):
    cmd = cc + ['-V']
    try:
        out, err = conf.cmd_and_log(cmd, output=0)
    except Errors.WafError as e:
        if not (hasattr(e, 'returncode') and hasattr(e, 'stdout') and hasattr(e, 'stderr')):
            conf.fatal('Could not find suncc %r' % cmd)
        out = e.stdout
        err = e.stderr
    version = (out or err)
    version = version.splitlines()[0]
    version_re = re.compile(
        r'cc: (studio.*?|\s+)?(sun\s+(c\+\+|c)|(WorkShop\s+Compilers))?\s+(?P<major>\d*)\.(?P<minor>\d*)', re.I
    ).search
    match = version_re(version)
    if match:
        k = match.groupdict()
        conf.env.CC_VERSION = (k['major'], k['minor'])
    else:
        conf.fatal('Could not determine the suncc version.')


@conf
def add_as_needed(self):
    if self.env.DEST_BINFMT == 'elf' and 'gcc' in (self.env.CXX_NAME, self.env.CC_NAME):
        self.env.append_unique('LINKFLAGS', '-Wl,--as-needed')


class cfgtask(Task.Task):
    def __init__(self, *k, **kw):
        Task.Task.__init__(self, *k, **kw)
        self.run_after = set()

    def display(self):
        return ''

    def runnable_status(self):
        for x in self.run_after:
            if not x.hasrun:
                return Task.ASK_LATER
        return Task.RUN_ME

    def uid(self):
        return Utils.SIG_NIL

    def signature(self):
        return Utils.SIG_NIL

    def run(self):
        conf = self.conf
        bld = Build.BuildContext(top_dir=conf.srcnode.abspath(), out_dir=conf.bldnode.abspath())
        bld.env = conf.env
        bld.init_dirs()
        bld.in_msg = 1
        bld.logger = self.logger
        bld.multicheck_task = self
        args = self.args
        try:
            if 'func' in args:
                bld.test(
                    build_fun=args['func'],
                    msg=args.get('msg', ''),
                    okmsg=args.get('okmsg', ''),
                    errmsg=args.get('errmsg', ''),
                )
            else:
                args['multicheck_mandatory'] = args.get('mandatory', True)
                args['mandatory'] = True
                try:
                    bld.check(**args)
                finally:
                    args['mandatory'] = args['multicheck_mandatory']
        except Exception:
            return 1

    def process(self):
        Task.Task.process(self)
        if 'msg' in self.args:
            with self.generator.bld.multicheck_lock:
                self.conf.start_msg(self.args['msg'])
                if self.hasrun == Task.NOT_RUN:
                    self.conf.end_msg('test cancelled', 'YELLOW')
                elif self.hasrun != Task.SUCCESS:
                    self.conf.end_msg(self.args.get('errmsg', 'no'), 'YELLOW')
                else:
                    self.conf.end_msg(self.args.get('okmsg', 'yes'), 'GREEN')


@conf
def multicheck(self, *k, **kw):
    self.start_msg(kw.get('msg', 'Executing %d configuration tests' % len(k)), **kw)
    for var in ('DEFINES', DEFKEYS):
        self.env.append_value(var, [])
    self.env.DEFINE_COMMENTS = self.env.DEFINE_COMMENTS or {}

    class par(object):
        def __init__(self):
            self.keep = False
            self.task_sigs = {}
            self.progress_bar = 0

        def total(self):
            return len(tasks)

        def to_log(self, *k, **kw):
            return

    bld = par()
    bld.keep = kw.get('run_all_tests', True)
    bld.imp_sigs = {}
    tasks = []
    id_to_task = {}
    for counter, dct in enumerate(k):
        x = Task.classes['cfgtask'](bld=bld, env=None)
        tasks.append(x)
        x.args = dct
        x.args['multicheck_counter'] = counter
        x.bld = bld
        x.conf = self
        x.args = dct
        x.logger = Logs.make_mem_logger(str(id(x)), self.logger)
        if 'id' in dct:
            id_to_task[dct['id']] = x
    for x in tasks:
        for key in Utils.to_list(x.args.get('before_tests', [])):
            tsk = id_to_task[key]
            if not tsk:
                raise ValueError('No test named %r' % key)
            tsk.run_after.add(x)
        for key in Utils.to_list(x.args.get('after_tests', [])):
            tsk = id_to_task[key]
            if not tsk:
                raise ValueError('No test named %r' % key)
            x.run_after.add(tsk)

    def it():
        yield tasks
        while 1:
            yield []

    bld.producer = p = Runner.Parallel(bld, Options.options.jobs)
    bld.multicheck_lock = Utils.threading.Lock()
    p.biter = it()
    self.end_msg('started')
    p.start()
    for x in tasks:
        x.logger.memhandler.flush()
    self.start_msg('-> processing test results')
    if p.error:
        for x in p.error:
            if getattr(x, 'err_msg', None):
                self.to_log(x.err_msg)
                self.end_msg('fail', color='RED')
                raise Errors.WafError('There is an error in the library, read config.log for more information')
    failure_count = 0
    for x in tasks:
        if x.hasrun not in (Task.SUCCESS, Task.NOT_RUN):
            failure_count += 1
    if failure_count:
        self.end_msg(kw.get('errmsg', '%s test failed' % failure_count), color='YELLOW', **kw)
    else:
        self.end_msg('all ok', **kw)
    for x in tasks:
        if x.hasrun != Task.SUCCESS:
            if x.args.get('mandatory', True):
                self.fatal(kw.get('fatalmsg') or 'One of the tests has failed, read config.log for more information')


@conf
def check_gcc_o_space(self, mode='c'):
    if int(self.env.CC_VERSION[0]) > 4:
        return
    self.env.stash()
    if mode == 'c':
        self.env.CCLNK_TGT_F = ['-o', '']
    elif mode == 'cxx':
        self.env.CXXLNK_TGT_F = ['-o', '']
    features = '%s %sshlib' % (mode, mode)
    try:
        self.check(
            msg='Checking if the -o link must be split from arguments', fragment=SNIP_EMPTY_PROGRAM, features=features
        )
    except self.errors.ConfigurationError:
        self.env.revert()
    else:
        self.env.commit()
