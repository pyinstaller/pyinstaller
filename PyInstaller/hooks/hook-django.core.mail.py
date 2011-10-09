# Copyright (C) 2009, Lorenzo Berni
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
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

# django.core.mail uses part of the email package.
# Problem is: when using runserver with autoreload mode, the thread that
# checks fore changed files unwillingly trigger further imports within
# the email package because of the LazyImporter in email (used in 2.5 for
# backward compatibility).
# We then need to name those modules as hidden imports, otherwise at
# runtime the autoreload thread will complain with a traceback.
hiddenimports = [
    'email.mime.message',
    'email.mime.image',
    'email.mime.text',
    'email.mime.multipart',
    'email.mime.audio'
]
