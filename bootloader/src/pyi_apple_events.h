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

#include <Carbon/Carbon.h>

typedef struct _pyi_context PYI_CONTEXT;

/* Context structure for keeping track of data */
typedef struct _apple_event_handler_context
{
    /* Event handlers for argv-emu / event forwarding */
    Boolean installed; /* Are handlers installed? */

    EventHandlerUPP upp_handler; /* UPP for event handler callback */
    EventHandlerRef handler_ref; /* Reference to installed event handler */

    /* Event handler callbacks for individual AppleEvent types */
    AEEventHandlerUPP upp_handler_oapp;
    AEEventHandlerUPP upp_handler_odoc;
    AEEventHandlerUPP upp_handler_gurl;
    AEEventHandlerUPP upp_handler_rapp;
    AEEventHandlerUPP upp_handler_actv;

    /* Deferred/pending event forwarding */
    Boolean has_pending_event; /* Flag indicating that pending_event is valid */
    unsigned int retry_count; /* Retry count for send attempts */
    AppleEvent pending_event; /* Copy of the event */

    /* Event types used when registering events. The single entry should
     * be initialized to {kEventClassAppleEvent, kEventAppleEvent}
     * when handlers are being set up. */
    EventTypeSpec event_types[1];
} APPLE_EVENT_HANDLER_CONTEXT;


/* Install Apple Event handlers. Requires PYI_CONTEXT as argument, in
 * order to pass the pointer to callbacks. */
int pyi_apple_install_event_handlers(PYI_CONTEXT *pyi_ctx);

/* Uninstall Apple Event handlers */
int pyi_apple_uninstall_event_handlers(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx);

/*
 * Process Apple Events, either appending them to sys.argv (if argv-emu
 * is enabled and child process is not (yet) running, or forwarding
 * them to the child process.
 */
void pyi_apple_process_events(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float timeout);

/*
 * Attempt to submit oapp event to ourselves in order to mitigate
 * issues with UI frameworks when argv-emu is used in onedir mode.
 */
void pyi_apple_submit_oapp_event(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx);

/* Check if we have a pending event that we need to forward. */
int pyi_apple_has_pending_event(const APPLE_EVENT_HANDLER_CONTEXT *ae_ctx);

/* Attempt to re-send the pending event after the specified delay. */
int pyi_apple_send_pending_event(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float delay);

/* Clean-up the pending event data and status. */
void pyi_apple_cleanup_pending_event(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx);

#endif  /* defined(__APPLE__) && defined(WINDOWED) */

#endif  /* PYI_APPLE_EVENTS_H */
