#
# Copyright (C) 2011 by Hartmut Goebel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA

__all__ = ('HOMEPATH', 'CONFIGDIR', 'DEFAULT_CONFIGFILE',
           'is_py24', 'is_win', 'is_cygwin', 'is_darwin',
           'is24', 'iswin', 'cygwin', 'darwin')

import os
import sys

HOMEPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONFIGDIR = HOMEPATH
DEFAULT_CONFIGFILE = os.path.join(CONFIGDIR, 'config.dat')

is_py24 = hasattr(sys, "version_info") and sys.version_info >= (2,4)

is_win = sys.platform.startswith('win')
is_cygwin = sys.platform == 'cygwin'
is_darwin = sys.platform.startswith('darwin')

# backward compatibility
is24 = is_py24
iswin = is_win
darwin = is_darwin
cygwin = is_cygwin
