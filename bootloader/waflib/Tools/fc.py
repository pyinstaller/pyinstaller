#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

from waflib import Utils, Task, Errors
from waflib.Tools import ccroot, fc_config, fc_scan
from waflib.TaskGen import extension
from waflib.Configure import conf

ccroot.USELIB_VARS['fc'] = set(['FCFLAGS', 'DEFINES', 'INCLUDES', 'FCPPFLAGS'])
ccroot.USELIB_VARS['fcprogram_test'] = ccroot.USELIB_VARS['fcprogram'] = set([
    'LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS', 'LDFLAGS'
])
ccroot.USELIB_VARS['fcshlib'] = set([
    'LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS', 'LDFLAGS'
])
ccroot.USELIB_VARS['fcstlib'] = set(['ARFLAGS', 'LINKDEPS'])


@extension('.f', '.F', '.f90', '.F90', '.for', '.FOR', '.f95', '.F95', '.f03', '.F03', '.f08', '.F08')
def fc_hook(self, node):
    return self.create_compiled_task('fc', node)


@conf
def modfile(conf, name):
    if name.find(':') >= 0:
        separator = conf.env.FC_SUBMOD_SEPARATOR or '@'
        modpath = name.split(':')
        modname = modpath[0] + separator + modpath[-1]
        suffix = conf.env.FC_SUBMOD_SUFFIX or '.smod'
    else:
        modname = name
        suffix = '.mod'
    return {
        'lower': modname.lower() + suffix.lower(),
        'lower.MOD': modname.lower() + suffix.upper(),
        'UPPER.mod': modname.upper() + suffix.lower(),
        'UPPER': modname.upper() + suffix.upper()
    }[conf.env.FC_MOD_CAPITALIZATION or 'lower']


def get_fortran_tasks(tsk):
    bld = tsk.generator.bld
    tasks = bld.get_tasks_group(bld.get_group_idx(tsk.generator))
    return [
        x for x in tasks
        if isinstance(x, fc) and not getattr(x, 'nomod', None) and not getattr(x, 'mod_fortran_done', None)
    ]


class fc(Task.Task):
    color = 'GREEN'
    run_str = '${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${_FCMODOUTFLAGS} ${FC_TGT_F}${TGT[0].abspath()} ${FC_SRC_F}${SRC[0].abspath()} ${FCPPFLAGS}'
    vars = ["FORTRANMODPATHFLAG"]

    def scan(self):
        tmp = fc_scan.fortran_parser(self.generator.includes_nodes)
        tmp.task = self
        tmp.start(self.inputs[0])
        return (tmp.nodes, tmp.names)

    def runnable_status(self):
        if getattr(self, 'mod_fortran_done', None):
            return super(fc, self).runnable_status()
        bld = self.generator.bld
        lst = get_fortran_tasks(self)
        for tsk in lst:
            tsk.mod_fortran_done = True
        for tsk in lst:
            ret = tsk.runnable_status()
            if ret == Task.ASK_LATER:
                for x in lst:
                    x.mod_fortran_done = None
                return Task.ASK_LATER
        ins = Utils.defaultdict(set)
        outs = Utils.defaultdict(set)
        for tsk in lst:
            key = tsk.uid()
            for x in bld.raw_deps[key]:
                if x.startswith('MOD@'):
                    name = bld.modfile(x.replace('MOD@', ''))
                    node = bld.srcnode.find_or_declare(name)
                    tsk.set_outputs(node)
                    outs[node].add(tsk)
        for tsk in lst:
            key = tsk.uid()
            for x in bld.raw_deps[key]:
                if x.startswith('USE@'):
                    name = bld.modfile(x.replace('USE@', ''))
                    node = bld.srcnode.find_resource(name)
                    if node and node not in tsk.outputs:
                        if not node in bld.node_deps[key]:
                            bld.node_deps[key].append(node)
                        ins[node].add(tsk)
        for k in ins.keys():
            for a in ins[k]:
                a.run_after.update(outs[k])
                for x in outs[k]:
                    self.generator.bld.producer.revdeps[x].add(a)
                tmp = []
                for t in outs[k]:
                    tmp.extend(t.outputs)
                a.dep_nodes.extend(tmp)
                a.dep_nodes.sort(key=lambda x: x.abspath())
        for tsk in lst:
            try:
                delattr(tsk, 'cache_sig')
            except AttributeError:
                pass
        return super(fc, self).runnable_status()


class fcprogram(ccroot.link_task):
    color = 'YELLOW'
    run_str = '${FC} ${LINKFLAGS} ${FCLNK_SRC_F}${SRC} ${FCLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FCSTLIB_MARKER} ${FCSTLIBPATH_ST:STLIBPATH} ${FCSTLIB_ST:STLIB} ${FCSHLIB_MARKER} ${FCLIBPATH_ST:LIBPATH} ${FCLIB_ST:LIB} ${LDFLAGS}'
    inst_to = '${BINDIR}'


class fcshlib(fcprogram):
    inst_to = '${LIBDIR}'


class fcstlib(ccroot.stlink_task):
    pass


class fcprogram_test(fcprogram):
    def runnable_status(self):
        ret = super(fcprogram_test, self).runnable_status()
        if ret == Task.SKIP_ME:
            ret = Task.RUN_ME
        return ret

    def exec_command(self, cmd, **kw):
        bld = self.generator.bld
        kw['shell'] = isinstance(cmd, str)
        kw['stdout'] = kw['stderr'] = Utils.subprocess.PIPE
        kw['cwd'] = self.get_cwd()
        bld.out = bld.err = ''
        bld.to_log('command: %s\n' % cmd)
        kw['output'] = 0
        try:
            (bld.out, bld.err) = bld.cmd_and_log(cmd, **kw)
        except Errors.WafError:
            return -1
        if bld.out:
            bld.to_log('out: %s\n' % bld.out)
        if bld.err:
            bld.to_log('err: %s\n' % bld.err)
