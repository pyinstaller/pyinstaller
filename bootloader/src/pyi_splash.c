/*
 * ****************************************************************************
 * Copyright (c) 2013-2020, PyInstaller Development Team.
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
 * A splash screen is a graphical window in which a program-defined screen
 * is displayed. It is normally used to give the user visual feedback,
 * indicating that the program has been started.
 *
 * The splash screen resources must be in the form of the SPLASH structure.
 */

#include <stdlib.h>   /* malloc */
#include <string.h>   /* strncmp, strcpy, strcat */
#include <limits.h>   /* PATH_MAX */
#include <stdio.h>
#include <stdlib.h>

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_utils.h"
#include "pyi_win32_utils.h"
#include "pyi_splash.h"

/*
 * Description of the protocol between the bootloader and the
 * python interpreter
 * */
#define _IPC_MSG_FINISH 'c'
#define _IPC_MSG_UPDATE 'u'
typedef struct _ipc_message_head {
    char event_type;
    int  text_length;
} IPC_MESSAGE_HEAD;

/*****************************************************************
 * Platform-independent splash screen functions definition.
 *****************************************************************/

/*
 * Searches the CArchive for splash screen resources and loads them into
 * a SPLASH structure if necessary, which is then returned. If no splash
 * resources are available, NULL is returned.
 *
 * The splash resources are identified in the CArchive by the type
 * code 'ARCHIVE_ITEM_SPLASH'.
 *
 * The SPLASH structure is, if loaded from the archive,
 * in network endian format, so it must be converted when used.
 */
SPLASH *
pyi_splash_get(ARCHIVE_STATUS *status)
{
    SPLASH *splash = NULL;
    TOC *ptoc = status->tocbuff;

    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_SPLASH) {
            splash = (SPLASH *) pyi_arch_extract(status, ptoc);
            break;
        }
        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }

    return splash;
}

/*
 * Starts the splash screen.
 * This method should be a wrapper for the platform-specific methods.
 *
 * NOTE: It is important to note that the process which handles the splash
 *  screen will presumably run in a separate thread.
 *  No precautions are taken to make the splash resources multithreading safe.
 */
int
pyi_splash_launch(SPLASH *splash)
{
    VS("SPLASH: This bootloader does not support splash screen\n");
    return -1;
}

/*
 * This function creates a unidirectional named pipe.
 *
 * The named pipe is used for communication between the bootloader and
 * the Python interpreter. A name for the pipe is generated and returned.
 * This process retains the permissions to read from the pipe, the write
 * end is handled by the pyi_splash module in the Python interpreter.
 */
char *
pyi_splash_setup_ipc()
{
    char *_pipe_name;

    VS("SPLASH: This bootloader does not support splash screen\n");
    return NULL;
}
