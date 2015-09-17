#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
This module contains various helper functions for git DVCS
"""

import os
from ..compat import exec_command, exec_command_rc

def get_repo_revision():
    path = os.path # shortcut
    gitdir = path.normpath(path.join(path.dirname(__file__), '..','..', '.git'))
    cwd = os.path.dirname(gitdir)
    if not path.exists(gitdir):
        return ''
    try:
        rev = exec_command('git', 'rev-parse', '--short', 'HEAD', cwd=cwd).strip()
        if rev:
            # need to update index first to get reliable state
            exec_command_rc('git', 'update-index', '-q', '--refresh', cwd=cwd)
            changed = exec_command_rc('git', 'diff-index', '--quiet', 'HEAD', cwd=cwd)
            if changed:
                rev = rev + '-mod'
            # According to pep440 local version identifier starts with '+'.
            return '+' + rev
    except:
        pass
    return ''


if __name__ == '__main__':
    print(get_repo_revision())
