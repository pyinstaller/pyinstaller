#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

from __future__ import with_statement
try:
    from xml.sax import make_parser
    from xml.sax.handler import ContentHandler
except ImportError:
    has_xml = False
    ContentHandler = object
else:
    has_xml = True
import os, sys, re
from waflib.Tools import cxx
from waflib import Build, Task, Utils, Options, Errors, Context
from waflib.TaskGen import feature, after_method, extension, before_method
from waflib.Configure import conf
from waflib import Logs

MOC_H = ['.h', '.hpp', '.hxx', '.hh']
EXT_RCC = ['.qrc']
EXT_UI = ['.ui']
EXT_QT5 = ['.cpp', '.cc', '.cxx', '.C']


class qxx(Task.classes['cxx']):
    def __init__(self, *k, **kw):
        Task.Task.__init__(self, *k, **kw)
        self.moc_done = 0

    def runnable_status(self):
        if self.moc_done:
            return Task.Task.runnable_status(self)
        else:
            for t in self.run_after:
                if not t.hasrun:
                    return Task.ASK_LATER
            self.add_moc_tasks()
            return Task.Task.runnable_status(self)

    def create_moc_task(self, h_node, m_node):
        try:
            moc_cache = self.generator.bld.moc_cache
        except AttributeError:
            moc_cache = self.generator.bld.moc_cache = {}
        try:
            return moc_cache[h_node]
        except KeyError:
            tsk = moc_cache[h_node] = Task.classes['moc'](env=self.env, generator=self.generator)
            tsk.set_inputs(h_node)
            tsk.set_outputs(m_node)
            tsk.env.append_unique('MOC_FLAGS', '-i')
            if self.generator:
                self.generator.tasks.append(tsk)
            gen = self.generator.bld.producer
            gen.outstanding.append(tsk)
            gen.total += 1
            return tsk
        else:
            delattr(self, 'cache_sig')

    def add_moc_tasks(self):
        node = self.inputs[0]
        bld = self.generator.bld
        if bld.is_install == Build.UNINSTALL:
            return
        try:
            self.signature()
        except KeyError:
            pass
        else:
            delattr(self, 'cache_sig')
        include_nodes = [node.parent] + self.generator.includes_nodes
        moctasks = []
        mocfiles = set()
        for d in bld.raw_deps.get(self.uid(), []):
            if not d.endswith('.moc'):
                continue
            if d in mocfiles:
                continue
            mocfiles.add(d)
            h_node = None
            base2 = d[:-4]
            prefix = node.name[:node.name.rfind('.')]
            if base2 == prefix:
                h_node = node
            else:
                for x in include_nodes:
                    for e in MOC_H:
                        h_node = x.find_node(base2 + e)
                        if h_node:
                            break
                    else:
                        continue
                    break
            if h_node:
                m_node = h_node.change_ext('.moc')
            else:
                raise Errors.WafError('No source found for %r which is a moc file' % d)
            task = self.create_moc_task(h_node, m_node)
            moctasks.append(task)
        self.run_after.update(set(moctasks))
        self.moc_done = 1


class trans_update(Task.Task):
    run_str = '${QT_LUPDATE} ${SRC} -ts ${TGT}'
    color = 'BLUE'


class XMLHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)
        self.buf = []
        self.files = []

    def startElement(self, name, attrs):
        if name == 'file':
            self.buf = []

    def endElement(self, name):
        if name == 'file':
            self.files.append(str(''.join(self.buf)))

    def characters(self, cars):
        self.buf.append(cars)


@extension(*EXT_RCC)
def create_rcc_task(self, node):
    rcnode = node.change_ext('_rc.%d.cpp' % self.idx)
    self.create_task('rcc', node, rcnode)
    cpptask = self.create_task('cxx', rcnode, rcnode.change_ext('.o'))
    try:
        self.compiled_tasks.append(cpptask)
    except AttributeError:
        self.compiled_tasks = [cpptask]
    return cpptask


@extension(*EXT_UI)
def create_uic_task(self, node):
    try:
        uic_cache = self.bld.uic_cache
    except AttributeError:
        uic_cache = self.bld.uic_cache = {}
    if node not in uic_cache:
        uictask = uic_cache[node] = self.create_task('ui5', node)
        uictask.outputs = [node.parent.find_or_declare(self.env.ui_PATTERN % node.name[:-3])]


@extension('.ts')
def add_lang(self, node):
    self.lang = self.to_list(getattr(self, 'lang', [])) + [node]


@feature('qt5')
@before_method('process_source')
def process_mocs(self):
    lst = self.to_nodes(getattr(self, 'moc', []))
    self.source = self.to_list(getattr(self, 'source', []))
    for x in lst:
        prefix = x.name[:x.name.rfind('.')]
        moc_target = 'moc_%s.%d.cpp' % (prefix, self.idx)
        moc_node = x.parent.find_or_declare(moc_target)
        self.source.append(moc_node)
        self.create_task('moc', x, moc_node)


@feature('qt5')
@after_method('apply_link')
def apply_qt5(self):
    if getattr(self, 'lang', None):
        qmtasks = []
        for x in self.to_list(self.lang):
            if isinstance(x, str):
                x = self.path.find_resource(x + '.ts')
            qmtasks.append(self.create_task('ts2qm', x, x.change_ext('.%d.qm' % self.idx)))
        if getattr(self, 'update', None) and Options.options.trans_qt5:
            cxxnodes = [a.inputs[0] for a in self.compiled_tasks
                        ] + [a.inputs[0] for a in self.tasks if a.inputs and a.inputs[0].name.endswith('.ui')]
            for x in qmtasks:
                self.create_task('trans_update', cxxnodes, x.inputs)
        if getattr(self, 'langname', None):
            qmnodes = [x.outputs[0] for x in qmtasks]
            rcnode = self.langname
            if isinstance(rcnode, str):
                rcnode = self.path.find_or_declare(rcnode + ('.%d.qrc' % self.idx))
            t = self.create_task('qm2rcc', qmnodes, rcnode)
            k = create_rcc_task(self, t.outputs[0])
            self.link_task.inputs.append(k.outputs[0])
    lst = []
    for flag in self.to_list(self.env.CXXFLAGS):
        if len(flag) < 2:
            continue
        f = flag[0:2]
        if f in ('-D', '-I', '/D', '/I'):
            if (f[0] == '/'):
                lst.append('-' + flag[1:])
            else:
                lst.append(flag)
    self.env.append_value('MOC_FLAGS', lst)


@extension(*EXT_QT5)
def cxx_hook(self, node):
    return self.create_compiled_task('qxx', node)


class rcc(Task.Task):
    color = 'BLUE'
    run_str = '${QT_RCC} -name ${tsk.rcname()} ${SRC[0].abspath()} ${RCC_ST} -o ${TGT}'
    ext_out = ['.h']

    def rcname(self):
        return os.path.splitext(self.inputs[0].name)[0]

    def scan(self):
        if not has_xml:
            Logs.error('No xml.sax support was found, rcc dependencies will be incomplete!')
            return ([], [])
        parser = make_parser()
        curHandler = XMLHandler()
        parser.setContentHandler(curHandler)
        with open(self.inputs[0].abspath(), 'r') as f:
            parser.parse(f)
        nodes = []
        names = []
        root = self.inputs[0].parent
        for x in curHandler.files:
            nd = root.find_resource(x)
            if nd:
                nodes.append(nd)
            else:
                names.append(x)
        return (nodes, names)

    def quote_flag(self, x):
        return x


class moc(Task.Task):
    color = 'BLUE'
    run_str = '${QT_MOC} ${MOC_FLAGS} ${MOCCPPPATH_ST:INCPATHS} ${MOCDEFINES_ST:DEFINES} ${SRC} ${MOC_ST} ${TGT}'

    def quote_flag(self, x):
        return x


class ui5(Task.Task):
    color = 'BLUE'
    run_str = '${QT_UIC} ${SRC} -o ${TGT}'
    ext_out = ['.h']


class ts2qm(Task.Task):
    color = 'BLUE'
    run_str = '${QT_LRELEASE} ${QT_LRELEASE_FLAGS} ${SRC} -qm ${TGT}'


class qm2rcc(Task.Task):
    color = 'BLUE'
    after = 'ts2qm'

    def run(self):
        txt = '\n'.join(['<file>%s</file>' % k.path_from(self.outputs[0].parent) for k in self.inputs])
        code = '<!DOCTYPE RCC><RCC version="1.0">\n<qresource>\n%s\n</qresource>\n</RCC>' % txt
        self.outputs[0].write(code)


def configure(self):
    self.find_qt5_binaries()
    self.set_qt5_libs_dir()
    self.set_qt5_libs_to_check()
    self.set_qt5_defines()
    self.find_qt5_libraries()
    self.add_qt5_rpath()
    self.simplify_qt5_libs()
    if not has_xml:
        Logs.error('No xml.sax support was found, rcc dependencies will be incomplete!')
    if 'COMPILER_CXX' not in self.env:
        self.fatal('No CXX compiler defined: did you forget to configure compiler_cxx first?')
    frag = '#include <QMap>\nint main(int argc, char **argv) {QMap<int,int> m;return m.keys().size();}\n'
    uses = 'QT5CORE'
    for flag in [[], '-fPIE', '-fPIC', '-std=c++11', ['-std=c++11', '-fPIE'], ['-std=c++11', '-fPIC']]:
        msg = 'See if Qt files compile '
        if flag:
            msg += 'with %s' % flag
        try:
            self.check(features='qt5 cxx', use=uses, uselib_store='qt5', cxxflags=flag, fragment=frag, msg=msg)
        except self.errors.ConfigurationError:
            pass
        else:
            break
    else:
        self.fatal('Could not build a simple Qt application')
    if Utils.unversioned_sys_platform() == 'freebsd':
        frag = '#include <QMap>\nint main(int argc, char **argv) {QMap<int,int> m;return m.keys().size();}\n'
        try:
            self.check(
                features='qt5 cxx cxxprogram',
                use=uses,
                fragment=frag,
                msg='Can we link Qt programs on FreeBSD directly?'
            )
        except self.errors.ConfigurationError:
            self.check(
                features='qt5 cxx cxxprogram',
                use=uses,
                uselib_store='qt5',
                libpath='/usr/local/lib',
                fragment=frag,
                msg='Is /usr/local/lib required?'
            )


@conf
def find_qt5_binaries(self):
    env = self.env
    opt = Options.options
    qtdir = getattr(opt, 'qtdir', '')
    qtbin = getattr(opt, 'qtbin', '')
    paths = []
    if qtdir:
        qtbin = os.path.join(qtdir, 'bin')
    if not qtdir:
        qtdir = self.environ.get('QT5_ROOT', '')
        qtbin = self.environ.get('QT5_BIN') or os.path.join(qtdir, 'bin')
    if qtbin:
        paths = [qtbin]
    if not qtdir:
        paths = self.environ.get('PATH', '').split(os.pathsep)
        paths.extend(['/usr/share/qt5/bin', '/usr/local/lib/qt5/bin'])
        try:
            lst = Utils.listdir('/usr/local/Trolltech/')
        except OSError:
            pass
        else:
            if lst:
                lst.sort()
                lst.reverse()
                qtdir = '/usr/local/Trolltech/%s/' % lst[0]
                qtbin = os.path.join(qtdir, 'bin')
                paths.append(qtbin)
    cand = None
    prev_ver = ['5', '0', '0']
    for qmk in ('qmake-qt5', 'qmake5', 'qmake'):
        try:
            qmake = self.find_program(qmk, path_list=paths)
        except self.errors.ConfigurationError:
            pass
        else:
            try:
                version = self.cmd_and_log(qmake + ['-query', 'QT_VERSION']).strip()
            except self.errors.WafError:
                pass
            else:
                if version:
                    new_ver = version.split('.')
                    if new_ver > prev_ver:
                        cand = qmake
                        prev_ver = new_ver
    if not cand:
        try:
            self.find_program('qtchooser')
        except self.errors.ConfigurationError:
            pass
        else:
            cmd = self.env.QTCHOOSER + ['-qt=5', '-run-tool=qmake']
            try:
                version = self.cmd_and_log(cmd + ['-query', 'QT_VERSION'])
            except self.errors.WafError:
                pass
            else:
                cand = cmd
    if cand:
        self.env.QMAKE = cand
    else:
        self.fatal('Could not find qmake for qt5')
    self.env.QT_HOST_BINS = qtbin = self.cmd_and_log(self.env.QMAKE + ['-query', 'QT_HOST_BINS']).strip()
    paths.insert(0, qtbin)

    def find_bin(lst, var):
        if var in env:
            return
        for f in lst:
            try:
                ret = self.find_program(f, path_list=paths)
            except self.errors.ConfigurationError:
                pass
            else:
                env[var] = ret
                break

    find_bin(['uic-qt5', 'uic'], 'QT_UIC')
    if not env.QT_UIC:
        self.fatal('cannot find the uic compiler for qt5')
    self.start_msg('Checking for uic version')
    uicver = self.cmd_and_log(env.QT_UIC + ['-version'], output=Context.BOTH)
    uicver = ''.join(uicver).strip()
    uicver = uicver.replace('Qt User Interface Compiler ', '').replace('User Interface Compiler for Qt', '')
    self.end_msg(uicver)
    if uicver.find(' 3.') != -1 or uicver.find(' 4.') != -1:
        self.fatal('this uic compiler is for qt3 or qt4, add uic for qt5 to your path')
    find_bin(['moc-qt5', 'moc'], 'QT_MOC')
    find_bin(['rcc-qt5', 'rcc'], 'QT_RCC')
    find_bin(['lrelease-qt5', 'lrelease'], 'QT_LRELEASE')
    find_bin(['lupdate-qt5', 'lupdate'], 'QT_LUPDATE')
    env.UIC_ST = '%s -o %s'
    env.MOC_ST = '-o'
    env.ui_PATTERN = 'ui_%s.h'
    env.QT_LRELEASE_FLAGS = ['-silent']
    env.MOCCPPPATH_ST = '-I%s'
    env.MOCDEFINES_ST = '-D%s'


@conf
def set_qt5_libs_dir(self):
    env = self.env
    qtlibs = getattr(Options.options, 'qtlibs', None) or self.environ.get('QT5_LIBDIR')
    if not qtlibs:
        try:
            qtlibs = self.cmd_and_log(env.QMAKE + ['-query', 'QT_INSTALL_LIBS']).strip()
        except Errors.WafError:
            qtdir = self.cmd_and_log(env.QMAKE + ['-query', 'QT_INSTALL_PREFIX']).strip()
            qtlibs = os.path.join(qtdir, 'lib')
    self.msg('Found the Qt5 libraries in', qtlibs)
    env.QTLIBS = qtlibs


@conf
def find_single_qt5_lib(self, name, uselib, qtlibs, qtincludes, force_static):
    env = self.env
    if force_static:
        exts = ('.a', '.lib')
        prefix = 'STLIB'
    else:
        exts = ('.so', '.lib')
        prefix = 'LIB'

    def lib_names():
        for x in exts:
            for k in ('', '5') if Utils.is_win32 else ['']:
                for p in ('lib', ''):
                    yield (p, name, k, x)

    for tup in lib_names():
        k = ''.join(tup)
        path = os.path.join(qtlibs, k)
        if os.path.exists(path):
            if env.DEST_OS == 'win32':
                libval = ''.join(tup[:-1])
            else:
                libval = name
            env.append_unique(prefix + '_' + uselib, libval)
            env.append_unique('%sPATH_%s' % (prefix, uselib), qtlibs)
            env.append_unique('INCLUDES_' + uselib, qtincludes)
            env.append_unique('INCLUDES_' + uselib, os.path.join(qtincludes, name.replace('Qt5', 'Qt')))
            return k
    return False


@conf
def find_qt5_libraries(self):
    env = self.env
    qtincludes = self.environ.get('QT5_INCLUDES') or self.cmd_and_log(env.QMAKE +
                                                                      ['-query', 'QT_INSTALL_HEADERS']).strip()
    force_static = self.environ.get('QT5_FORCE_STATIC')
    try:
        if self.environ.get('QT5_XCOMPILE'):
            self.fatal('QT5_XCOMPILE Disables pkg-config detection')
        self.check_cfg(atleast_pkgconfig_version='0.1')
    except self.errors.ConfigurationError:
        for i in self.qt5_vars:
            uselib = i.upper()
            if Utils.unversioned_sys_platform() == 'darwin':
                fwk = i.replace('Qt5', 'Qt')
                frameworkName = fwk + '.framework'
                qtDynamicLib = os.path.join(env.QTLIBS, frameworkName, fwk)
                if os.path.exists(qtDynamicLib):
                    env.append_unique('FRAMEWORK_' + uselib, fwk)
                    env.append_unique('FRAMEWORKPATH_' + uselib, env.QTLIBS)
                    self.msg('Checking for %s' % i, qtDynamicLib, 'GREEN')
                else:
                    self.msg('Checking for %s' % i, False, 'YELLOW')
                env.append_unique('INCLUDES_' + uselib, os.path.join(env.QTLIBS, frameworkName, 'Headers'))
            else:
                ret = self.find_single_qt5_lib(i, uselib, env.QTLIBS, qtincludes, force_static)
                if not force_static and not ret:
                    ret = self.find_single_qt5_lib(i, uselib, env.QTLIBS, qtincludes, True)
                self.msg('Checking for %s' % i, ret, 'GREEN' if ret else 'YELLOW')
    else:
        path = '%s:%s:%s/pkgconfig:/usr/lib/qt5/lib/pkgconfig:/opt/qt5/lib/pkgconfig:/usr/lib/qt5/lib:/opt/qt5/lib' % (
            self.environ.get('PKG_CONFIG_PATH', ''), env.QTLIBS, env.QTLIBS
        )
        for i in self.qt5_vars:
            self.check_cfg(
                package=i, args='--cflags --libs', mandatory=False, force_static=force_static, pkg_config_path=path
            )


@conf
def simplify_qt5_libs(self):
    env = self.env

    def process_lib(vars_, coreval):
        for d in vars_:
            var = d.upper()
            if var == 'QTCORE':
                continue
            value = env['LIBPATH_' + var]
            if value:
                core = env[coreval]
                accu = []
                for lib in value:
                    if lib in core:
                        continue
                    accu.append(lib)
                env['LIBPATH_' + var] = accu

    process_lib(self.qt5_vars, 'LIBPATH_QTCORE')


@conf
def add_qt5_rpath(self):
    env = self.env
    if getattr(Options.options, 'want_rpath', False):

        def process_rpath(vars_, coreval):
            for d in vars_:
                var = d.upper()
                value = env['LIBPATH_' + var]
                if value:
                    core = env[coreval]
                    accu = []
                    for lib in value:
                        if var != 'QTCORE':
                            if lib in core:
                                continue
                        accu.append('-Wl,--rpath=' + lib)
                    env['RPATH_' + var] = accu

        process_rpath(self.qt5_vars, 'LIBPATH_QTCORE')


@conf
def set_qt5_libs_to_check(self):
    self.qt5_vars = Utils.to_list(getattr(self, 'qt5_vars', []))
    if not self.qt5_vars:
        dirlst = Utils.listdir(self.env.QTLIBS)
        pat = self.env.cxxshlib_PATTERN
        if Utils.is_win32:
            pat = pat.replace('.dll', '.lib')
        if self.environ.get('QT5_FORCE_STATIC'):
            pat = self.env.cxxstlib_PATTERN
        if Utils.unversioned_sys_platform() == 'darwin':
            pat = r"%s\.framework"
        re_qt = re.compile(pat % 'Qt5?(?P<name>.*)' + '$')
        for x in dirlst:
            m = re_qt.match(x)
            if m:
                self.qt5_vars.append("Qt5%s" % m.group('name'))
        if not self.qt5_vars:
            self.fatal('cannot find any Qt5 library (%r)' % self.env.QTLIBS)
    qtextralibs = getattr(Options.options, 'qtextralibs', None)
    if qtextralibs:
        self.qt5_vars.extend(qtextralibs.split(','))


@conf
def set_qt5_defines(self):
    if sys.platform != 'win32':
        return
    for x in self.qt5_vars:
        y = x.replace('Qt5', 'Qt')[2:].upper()
        self.env.append_unique('DEFINES_%s' % x.upper(), 'QT_%s_LIB' % y)


def options(opt):
    opt.add_option(
        '--want-rpath', action='store_true', default=False, dest='want_rpath', help='enable the rpath for qt libraries'
    )
    for i in 'qtdir qtbin qtlibs'.split():
        opt.add_option('--' + i, type='string', default='', dest=i)
    opt.add_option(
        '--translate', action='store_true', help='collect translation strings', dest='trans_qt5', default=False
    )
    opt.add_option(
        '--qtextralibs',
        type='string',
        default='',
        dest='qtextralibs',
        help='additional qt libraries on the system to add to default ones, comma separated'
    )
