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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Enchant hook test.


import sys
import enchant


backends = [x.name for x in enchant.Broker().describe()]
langs = enchant.list_languages()
dicts = [x[0] for x in enchant.list_dicts()]


# At least one backend should be available
if len(backends) < 1:
    print('E: No dictionary backend available')
    exit(1)

if len(dicts) < 1:
    print('W: No dictionary available')

print(80 * '-')
print('PYTHONPATH: %s' % sys.path)
print(80 * '-')
print('Backends: ' + ', '.join(backends))
print('Languages: %s' % ', '.join(langs))
print('Dictionaries: %s' % dicts)
print(80 * '-')

# Try spell checking if English is availale
l = 'en_US'
if l in langs:
    d = enchant.Dict(l)
    print('d.check("hallo") %s' % d.check('hallo'))
    print('d.check("halllo") %s' % d.check('halllo'))
    print('d.suggest("halllo") %s' % d.suggest('halllo'))
