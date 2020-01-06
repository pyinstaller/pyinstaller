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

# Hook for speech_recognition: https://pypi.python.org/pypi/SpeechRecognition/
# Tested on Windows 8.1 x64 with SpeechRecognition 1.5

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("speech_recognition")
