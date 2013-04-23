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


from PyInstaller import compat

def get_repo_revision():
    try:
        rev = compat.exec_command('git', 'rev-parse', '--short', 'HEAD').strip()
        if rev:
            return rev
    except:
        pass
    return ''


if __name__ == '__main__':
    print get_repo_revision()
