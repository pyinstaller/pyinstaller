# This module contains various helper functions for git DVCS
#
# Copyright (C) 2011, hartmut Goebel
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os
from PyInstaller import compat

def _findrepo():
    p = os.path.abspath(os.path.dirname(__file__))
    while not os.path.isdir(os.path.join(p, ".git")):
        oldp, p = p, os.path.dirname(p)
        if p == oldp:
            return None
    return os.path.join(p, ".git")

def get_repo_revision():
    '''
    Returns git revision string somelike `git rev-parse --short HEAD`
    does.

    Returns an empty string if anything goes wrong, such as missing
    .hg files or an unexpected format of internal HG files or no
    mercurial repository found.
    '''
    repopath = _findrepo()
    if not repopath:
        return ''
    try:
        head = open(os.path.join(repopath, 'HEAD'), 'rU').read()
        for l in head.splitlines():
            l = l.split()
            if l[0] == 'ref:':
                ref = l[1]
                break
        else:
            ref = None
        if ref:
            rev = open(os.path.join(repopath, ref), 'rU').read()
            rev = rev[:7]
            if rev:
                return rev
    except IOError:
        pass
    try:
        rev = compat.exec_command('git', 'rev-parse', '--short', 'HEAD').strip()
        if rev:
            return rev
    except:
        pass
    return ''


if __name__ == '__main__':
    print get_repo_revision()
