#
# Copyright (C) 2012, Martin Zibricky
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


# Test inclusion of fake 'site' module.

import site


# Default values in fake 'site' module should be False, None or empty list.

if not site.ENABLE_USER_SITE == False:
    raise SystemExit('ENABLE_USER_SITE not False.')
if not site.PREFIXES == []:
    raise SystemExit('PREFIXES not empty list.')

if site.USER_SITE is not None and site.USER_BASE is not None:
    raise SystemExit('USER_SITE or USER_BASE not None.')
