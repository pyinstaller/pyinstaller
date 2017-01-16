#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
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
from ..compat import exec_command, exec_command_rc, FileNotFoundError

try:
    WindowsError
except NameError:
    # No running on Windows
    WindowsError = FileNotFoundError

def get_repo_revision():
    path = os.path # shortcut
    gitdir = path.normpath(path.join(path.dirname(os.path.abspath(__file__)), '..', '..', '.git'))
    cwd = os.path.dirname(gitdir)
    if not path.exists(gitdir):
        try:
            from ._gitrevision import rev
            if not rev.startswith('$'):
                # the format specifier has been substituted
                return '+' + rev
        except ImportError:
            pass
        return ''
    try:
        # need to update index first to get reliable state
        exec_command_rc('git', 'update-index', '-q', '--refresh', cwd=cwd)
        recent = exec_command('git', 'describe', '--long', '--dirty', '--tag',
                              cwd=cwd).strip()
        if recent.endswith('-dirty'):
            tag, changes, rev, dirty = recent.rsplit('-', 3)
            rev = rev + '.mod'
        else:
            tag, changes, rev = recent.rsplit('-', 2)
        if changes == '0':
            return ''
        # According to pep440 local version identifier starts with '+'.
        return '+' + rev
    except (FileNotFoundError, WindowsError):
        # Be silent when git command is not found.
        pass
    return ''


if __name__ == '__main__':
    print(get_repo_revision())
