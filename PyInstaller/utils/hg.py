# This module contains various helper functions
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Absolute imports are not available prior to Python 2.5. Thus this
# module most not be named `mercurial` until we require Python 2.5 or
# newer.

import os

def _findrepo():
    p = os.path.abspath(os.path.dirname(__file__))
    while not os.path.isdir(os.path.join(p, ".hg")):
        oldp, p = p, os.path.dirname(p)
        if p == oldp:
            return None
    return p


def get_repo_revision():
    '''
    Returns mercurial revision string somelike `hg identify` does.

    Format is rev1:short-id1+;rev2:short-id2+

    Returns an empty string if anything goes wrong, such as missing
    .hg files or an unexpected format of internal HG files or no
    mercurial repository found.
    '''
    repopath = _findrepo()
    if not repopath:
        return ''
    # first try to use mercurial itself
    try:
        import mercurial.hg, mercurial.ui, mercurial.scmutil
        from mercurial.node import short as hexfunc
    except ImportError:
        pass
    else:
        ui = mercurial.ui.ui()
        repo = mercurial.hg.repository(ui, repopath)
        parents = repo[None].parents()
        changed = filter(None, repo.status()) and "+" or ""
        return ';'.join(['%s:%s%s' % (p.rev(), hexfunc(p.node()), changed)
                         for p in parents])

    # todo: mercurial not found, try to retrieve the information
    # ourselves
    return ''

if __name__ == '__main__':
    print get_repo_revision()
