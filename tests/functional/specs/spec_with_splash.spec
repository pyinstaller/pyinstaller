# -*- coding: utf-8 ; mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import os

app_name = "spec_with_splash"

# This variable is set by pytest to change the test image bit count
# possible values: 24 or 32
bit_count = os.environ['_TEST_SPLASH_BITCOUNT']

splash = Splash('../data/splash/bitmap_%sbit.bmp' % bit_count,
                text_rect=(0, 0, 100, 50),
                text_color=0xFFFF00)

a = Analysis(['../scripts/pyi_interact_pyi_splash.py'])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts, 
          splash,
          exclude_binaries=True,
          name=app_name,
          debug=True,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name=app_name)
