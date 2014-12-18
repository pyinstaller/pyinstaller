#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test whether
# a) scapy packet layers are not included if neither scapy.all nor
#    scapy.layers.all are imported.
# b) packages are included if imported explicitly

# This test-case assumes, that layer modules are imported only if

NAME = 'hook-scapy.layers.all'

import scapy
try:
    import scapy.layers.inet
    raise Exception('Self-test of hook %s failed: package module found'
                    % NAME)
except ImportError, e:
    if not e.args[0].endswith(' scapy.layers.inet'):
        raise Exception('Self-test of hook %s failed: package module found '
                        'and has import errors.' % NAME)

import scapy.layers
try:
    import scapy.layers.inet
    raise Exception('Self-test of hook %s failed: package module found'
                    % NAME)
except ImportError, e:
    if not e.args[0].endswith(' scapy.layers.inet'):
        raise Exception('Self-test of hook %s failed: package module found '
                        'and has import errors.' % NAME)

# Explicitly import a single layer module. Note: This module MUST NOT
# import inet (neither directly nor indirectly), otherwise the test
# above fails.
import scapy.layers.ir
