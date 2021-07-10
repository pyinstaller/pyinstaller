/*
 * ****************************************************************************
 * Copyright (c) 2013-2021, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/*
 * On some platforms (e.g. Solaris, AIX) mkdtemp is not available.
 */
#ifndef __MKDTEMP__
#define __MKDTEMP__

#include <stddef.h>

static char*
mkdtemp(char *template)
{
    if (!mktemp(template) ) {
        return NULL;
    }

    if (mkdir(template, 0700) ) {
        return NULL;
    }
    return template;
}

#endif /* ifndef __MKDTEMP__ */
