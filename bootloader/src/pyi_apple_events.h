/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
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
 *
 * This allows the app bundle to open file by dragging and dropping it
 * onto app's icon in the macOS dock.
 */

#ifndef PYI_APPLE_EVENTS_H
#define PYI_APPLE_EVENTS_H

#if defined(__APPLE__) && defined(WINDOWED)

struct PYI_CONTEXT;
struct APPLE_EVENT_HANDLER_CONTEXT;


/* Install Apple Event handlers, and return instance of allocated context
 * structure. Requires PYI_CONTEXT as argument, in order to pass the
 * pointer to callbacks. */
struct APPLE_EVENT_HANDLER_CONTEXT *pyi_apple_install_event_handlers(struct PYI_CONTEXT *pyi_ctx);

/* Uninstall Apple Event handlers */
void pyi_apple_uninstall_event_handlers(struct APPLE_EVENT_HANDLER_CONTEXT **ae_ctx_ref);

/*
 * Process Apple Events, either appending them to sys.argv (if argv-emu
 * is enabled and child process is not (yet) running, or forwarding
 * them to the child process.
 */
void pyi_apple_process_events(struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float timeout);

/* Check if we have a pending event that we need to forward. */
int pyi_apple_has_pending_event(const struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx);

/* Attempt to re-send the pending event after the specified delay. */
int pyi_apple_send_pending_event(struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float delay);

/* Clean-up the pending event data and status. */
void pyi_apple_cleanup_pending_event(struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx);

/*
 * Attempt to submit oapp event to ourselves in order to mitigate
 * issues with UI frameworks when argv-emu is used in onedir mode.
 * NOTE: does not require AppleEvent handler context, and is in fact
 * intended to be used *after* the handler context is freed.
 */
void pyi_apple_submit_oapp_event();

#endif  /* defined(__APPLE__) && defined(WINDOWED) */

#endif  /* PYI_APPLE_EVENTS_H */
