# This module contains various helper functions
#
# Copyright (C) 2011, Martin Zibricky
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

import os.path
import re


def get_repo_revision():
    '''
    Returns SVN revision number.

    Returns 0 if anything goes wrong, such as missing .svn files or
    an unexpected format of internal SVN files or folder is not
    a svn working copy.

    See http://stackoverflow.com/questions/1449935/getting-svn-revision-number-into-a-program-automatically
    '''
    rev = 0
    path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    entries_path = os.path.join(path, '.svn', 'entries')

    try:
        entries = open(entries_path, 'rU').read()
    except IOError:
        pass
    else:
        # Versions >= 7 of the entries file are flat text.  The first line is
        # the version number. The next set of digits after 'dir' is the revision.
        if re.match('(\d+)', entries):
            rev_match = re.search('\d+\s+dir\s+(\d+)', entries)
            if rev_match:
                rev = rev_match.groups()[0]
        # Older XML versions of the file specify revision as an attribute of
        # the first entries node.
        else:
            from xml.dom import minidom
            dom = minidom.parse(entries_path)
            rev = dom.getElementsByTagName('entry')[0].getAttribute('revision')

    return rev
