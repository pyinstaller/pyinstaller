#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test-cases taken from issue #834

import scapy.all
scapy.all.IP

from scapy.all import IP


# Test-case taken from issue #202.

from scapy.all import *
DHCP # scapy.layers.dhcp.DHCP
BOOTP # scapy.layers.dhcp.BOOTP
DNS # scapy.layers.dns.DNS
ICMP # scapy.layers.inet.ICMP
