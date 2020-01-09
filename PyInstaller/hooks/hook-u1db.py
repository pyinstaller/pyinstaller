#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

"""
Pyinstaller hook for u1db module

This hook was tested with:
- u1db 0.1.4 : https://launchpad.net/u1db
- Python 2.7.10
- Linux Debian GNU/Linux unstable (sid)

Test script used for testing:

    import u1db
    db = u1db.open("mydb1.u1db", create=True)
    doc = db.create_doc({"key": "value"}, doc_id="testdoc")
    print doc.content
    print doc.doc_id
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('u1db')