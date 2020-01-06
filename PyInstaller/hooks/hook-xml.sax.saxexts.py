#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# xml.sax.saxexts
hiddenimports = ["xml.sax.drivers2.drv_pyexpat",
                 "xml.sax.drivers.drv_xmltok",
                 'xml.sax.drivers2.drv_xmlproc',
                 "xml.sax.drivers.drv_xmltoolkit",
                 "xml.sax.drivers.drv_xmllib",
                 "xml.sax.drivers.drv_xmldc",
                 'xml.sax.drivers.drv_pyexpat',
                 'xml.sax.drivers.drv_xmlproc_val',
                 'xml.sax.drivers.drv_htmllib',
                 'xml.sax.drivers.drv_sgmlop',
                 "xml.sax.drivers.drv_sgmllib",
            ]
