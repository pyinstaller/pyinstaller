#! /usr/bin/env python3
#-----------------------------------------------------------------------------
# Copyright (c) 2014-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
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

from waflib import Task, TaskGen


def configure(conf):
    conf.find_program('strip')
    conf.env.append_value('STRIPFLAGS', '')


class strip(Task.Task):
    run_str = '${STRIP} ${STRIPFLAGS} ${SRC}'
    color = 'BLUE'
    after = ['cprogram', 'cxxprogram', 'cshlib', 'cxxshlib', 'fcprogram', 'fcshlib']


@TaskGen.feature('strip')
@TaskGen.after('apply_link')
def add_strip_task(self):
    try:
        link_task = self.link_task
    except AttributeError:
        return
    self.create_task('strip', link_task.outputs[0])
