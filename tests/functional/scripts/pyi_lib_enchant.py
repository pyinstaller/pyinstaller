#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Enchant hook test. Tested with PyEnchant 1.6.6.

import sys
import enchant


print(80 * '-')
print('PYTHONPATH: %s' % sys.path)

# At least one backend should be available
backends = [x.name for x in enchant.Broker().describe()]
if len(backends) < 1:
    raise SystemExit('Error: No dictionary backend available')
print(80 * '-')
print('Backends: ' + ', '.join(backends))

# Usually en_US dictionary should be bundled.
langs = enchant.list_languages()
dicts = [x[0] for x in enchant.list_dicts()]
if len(dicts) < 1:
    raise SystemExit('No dictionary available')
print(80 * '-')
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
