/*
 * ****************************************************************************
 * Copyright (c) 2005-2021, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#ifdef _WIN32

// Windows code
int __declspec(dllexport) dummy(int arg)
{
    return arg + 12;
}

#else

// Unix code
int dummy(int arg)
{
    return arg + 12;
}

#endif
