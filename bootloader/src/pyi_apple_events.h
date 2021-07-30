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
 * Handling of Apple Events in macOS windowed (app bundle) mode:
 *  - argv emulation
 *  - event forwarding to child process
 */

#ifndef PYI_APPLE_EVENTS_H
#define PYI_APPLE_EVENTS_H

#if defined(__APPLE__) && defined(WINDOWED)

/*
 * Watch for OpenDocument AppleEvents and add the files passed in to the
 * sys.argv command line on the Python side.
 *
 * This allows on Mac OS X to open files when a file is dragged and dropped
 * on the App icon in the OS X dock.
 */
void pyi_process_apple_events(bool short_timeout);

#endif  /* defined(__APPLE__) && defined(WINDOWED) */

#endif  /* PYI_APPLE_EVENTS_H */
