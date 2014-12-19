#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
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
from PyInstaller import compat

def get_repo_revision():
    path = os.path # shortcut
    gitdir = path.normpath(path.join(path.dirname(__file__), '..','..', '.git'))
    if not path.exists(gitdir):
        return ''
    try:
        rev = compat.exec_command('git', 'rev-parse', '--short', 'HEAD').strip()
        if rev:
            # need to update index first to get reliable state
            compat.exec_command_rc('git', 'update-index', '-q', '--refresh')
            changed = compat.exec_command_rc('git', 'diff-index', '--quiet', 'HEAD')
            if changed:
                rev = rev + '-mod'
            return rev
    except:
        pass
    return ''


if __name__ == '__main__':
    print(get_repo_revision())
