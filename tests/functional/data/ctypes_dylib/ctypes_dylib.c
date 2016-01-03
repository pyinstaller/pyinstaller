/*
 * ****************************************************************************
 * Copyright (c) 2005-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
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
