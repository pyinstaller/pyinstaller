#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Since Python 2.5 email modules were renamed.
# Test that old-style email naming still works
# in Python 2.5+


from email.MIMEMultipart import MIMEMultipart
