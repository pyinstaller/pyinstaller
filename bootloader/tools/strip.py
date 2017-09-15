#! /usr/bin/env python

"""
Strip a program/library after it is created. Use this tool as an example.

Usage::

    bld.program(features='strip', source='main.c', target='foo')

By using::

    @TaskGen.feature('cprogram', 'cxxprogram', 'fcprogram')


If stripping at installation time is preferred, use the following::

    import shutil, os
    from waflib import Build
    from waflib.Tools import ccroot
    def copy_fun(self, src, tgt, **kw):
        shutil.copy2(src, tgt)
        os.chmod(tgt, kw.get('chmod', Utils.O644))
        try:
            tsk = kw['tsk']
        except KeyError:
    	    pass
        else:
    	    if isinstance(tsk.task, ccroot.link_task):
    		    self.cmd_and_log('strip %s' % tgt)
    Build.InstallContext.copy_fun = copy_fun
"""

def configure(conf):
    conf.find_program('strip')
    conf.env.append_value('STRIPFLAGS', '')

from waflib import Task, TaskGen
class strip(Task.Task):
    run_str = '${STRIP} ${STRIPFLAGS} ${SRC}'
    color   = 'BLUE'
    after   = ['cprogram', 'cxxprogram', 'cshlib', 'cxxshlib', 'fcprogram', 'fcshlib']

    # In AIX, if we strip the same file more than once, it will return none-zero value
    # thus, causing crash

    # The following is a kludge
    
    def _run_ignore_error(self):
        if hasattr(self, '_orig_run'):
            try:
                ret = self._orig_run()
            except:
                pass
            return 0
        else:
            return -1
    
    def process(self):
        if not hasattr(self, '_orig_run'):
            self._orig_run = self.run
            self.run = self._run_ignore_error
        super(Task.Task,self).process()

@TaskGen.feature('strip')
@TaskGen.after('apply_link')
def add_strip_task(self):
    try:
        link_task = self.link_task
    except AttributeError:
        return
    self.create_task('strip', link_task.outputs[0])
