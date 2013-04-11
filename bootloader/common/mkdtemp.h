/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */


/*
 * On some platforms (e.g. Solaris, AIX) mkdtemp is not available.
 */
#ifndef __MKDTEMP__
#define __MKDTEMP__

static char* mkdtemp(char *template)
{
   if( ! mktemp(template) )
       return NULL;
   if( mkdir(template, 0700) )
       return NULL;
   return template;
}

#endif
