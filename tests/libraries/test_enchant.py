#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


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
