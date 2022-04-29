/*
 * ****************************************************************************
 * Copyright (c) 2013-2022, PyInstaller Development Team.
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

#if defined(__APPLE__) && defined(WINDOWED)

#include <Carbon/Carbon.h>  /* AppleEventsT */
#include <ApplicationServices/ApplicationServices.h> /* GetProcessForPID, etc */

#include "pyi_global.h"
#include "pyi_utils.h"
#include "pyi_apple_events.h"


/* Not declared in modern headers but exists in Carbon libs since time immemorial
 * See: https://applescriptlibrary.files.wordpress.com/2013/11/apple-events-programming-guide.pdf */
extern Boolean ConvertEventRefToEventRecord(EventRef inEvent, EventRecord *outEvent);

/*
 * On Mac OS X this converts events from kAEOpenDocuments and kAEGetURL into sys.argv.
 * After startup, it also forwards kAEOpenDocuments and KAEGetURL events at runtime to the child process.
 *
 * TODO: The below can be simplified considerably if re-written in Objective C (e.g. put into pyi_utils_osx.m).
 */


/* Static context structure for keeping track of data */
static struct AppleEventHandlerContext
{
    /* Event handlers for argv-emu / event forwarding */
    Boolean installed;  /* Are handlers installed? */

    EventHandlerUPP upp_handler;  /* UPP for event handler callback */
    AEEventHandlerUPP upp_handler_ae;  /* UPP for AppleEvent handler callback */

    EventHandlerRef handler_ref;  /* Reference to installer event handler */

    /* Deferred/pending event forwarding */
    Boolean has_pending_event;  /* Flag indicating that pending_event is valid */
    unsigned int retry_count;  /* Retry count for send attempts */
    AppleEvent pending_event;  /* Copy of the event */
} _ae_ctx = {
    false,  /* installed */
    NULL,  /* handler */
    NULL,  /* handler_ae */
    NULL,  /* handler_ref */
    false,  /* has_pending_event */
    0,  /* retry count */
    {typeNull, nil},  /* pending event */
};

/* Event types list: used to register handler and to listen for events */
static const EventTypeSpec event_types_ae[] = {
    { kEventClassAppleEvent, kEventAppleEvent },
};


/* Convert a FourCharCode into a string (useful for debug). Returned buffer is a static buffer, so subsequent calls
 * may overwrite the same buffer. */
static const char *CC2Str(FourCharCode code) {
    /* support up to 3 calls on the same debug print line */
    static char bufs[3][5];
    static unsigned int bufsidx = 0;
    char *buf = bufs[bufsidx++ % 3u];
    snprintf(buf, 5, "%c%c%c%c", (code >> 24) & 0xFF, (code >> 16) & 0xFF, (code >> 8) & 0xFF, code & 0xFF);
    /* buffer is guaranteed to be nul terminated here */
    return buf;
}

/* Generic event forwarder -- forwards an event destined for this process to the child process,
 * copying its param object, if any. Parameter `theAppleEvent` may be NULL, in which case a new
 * event is created with the specified class and id (containing 0 params / no param object). */
static OSErr generic_forward_apple_event(const AppleEvent *const theAppleEvent /* NULL ok */,
                                         const AEEventClass eventClass, const AEEventID evtID,
                                         const char *const descStr)
{
    const FourCharCode evtCode = (FourCharCode)evtID;
    OSErr err;
    AppleEvent childEvent;
    AEAddressDesc target;
    DescType actualType = 0, typeCode = typeWildCard;
    char *buf = NULL; /* dynamic buffer to hold copied event param data */
    Size bufSize = 0, actualSize = 0;
    pid_t child_pid;

    VS("LOADER [AppleEvent]: Forwarder called for \"%s\".\n", descStr);

    child_pid = pyi_utils_get_child_pid();
    if (!child_pid) {
        /* Child not up yet -- there is no way to "forward" this before child started!. */
         VS("LOADER [AppleEvent]: Child not up yet (child_pid is 0)\n");
         return errAEEventNotHandled;
    }
    VS("LOADER [AppleEvent]: Forwarding '%s' event.\n", CC2Str(evtCode));
    err = AECreateDesc(typeKernelProcessID, &child_pid, sizeof(child_pid), &target);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to create AEAddressDesc: %d\n", (int)err);
        goto out;
    }
    VS("LOADER [AppleEvent]: Created AEAddressDesc.\n");
    err = AECreateAppleEvent(eventClass, evtID, &target, kAutoGenerateReturnID, kAnyTransactionID,
                             &childEvent);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to create event copy: %d\n", (int)err);
        goto release_desc;
    }
    VS("LOADER [AppleEvent]: Created AppleEvent instance for child process.\n");


    if (!theAppleEvent) {
        /* Calling code wants a new event created from scratch, we do so
         * here and it will have 0 params. Assumption: caller knows that
         * the event type in question normally has 0 params. */
        VS("LOADER [AppleEvent]: New AppleEvent class: '%s' code: '%s'\n",
           CC2Str((FourCharCode)eventClass), CC2Str((FourCharCode)evtID));
    } else {
        err = AESizeOfParam(theAppleEvent, keyDirectObject, &typeCode, &bufSize);
        if (err != noErr) {
            /* No params for this event */
            VS("LOADER [AppleEvent]: Failed to get size of param (error=%d) -- event '%s' may lack params.\n",
                (int)err, CC2Str(evtCode));
        } else  {
            /* This event has a param object, copy it. */

            VS("LOADER [AppleEvent]: Got size of param: %ld\n", (long)bufSize);
            buf = malloc(bufSize);
            if (!buf) {
                /* Failed to allocate buffer! */
                OTHERERROR("LOADER [AppleEvent]: Failed to allocate buffer of size %ld: %s\n",
                           (long)bufSize, strerror(errno));
                goto release_evt;
            }
            VS("LOADER [AppleEvent]: Allocated buffer of size: %ld\n", (long)bufSize);
            VS("LOADER [AppleEvent]: Getting param.\n");
            err = AEGetParamPtr(theAppleEvent, keyDirectObject, typeWildCard,
                                &actualType, buf, bufSize, &actualSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent]: Failed to get param data.\n");
                goto release_evt;
            }
            if (actualSize > bufSize) {
                /* From reading the Apple API docs, this should never happen, but it pays
                 * to program defensively here. */
                OTHERERROR("LOADER [AppleEvent]: Got param size=%ld > bufSize=%ld, error!\n",
                           (long)actualSize, (long)bufSize);
                goto release_evt;
            }
            VS("LOADER [AppleEvent]: Got param type=%x ('%s') size=%ld\n",
               (UInt32)actualType, CC2Str((FourCharCode)actualType), (long)actualSize);
            VS("LOADER [AppleEvent]: Putting param.\n");
            err = AEPutParamPtr(&childEvent, keyDirectObject, actualType, buf, actualSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent]: Failed to put param data.\n");
                goto release_evt;
            }
        }
    }
    VS("LOADER [AppleEvent]: Sending message...\n");
    err = AESendMessage(&childEvent, NULL, kAENoReply, kAEDefaultTimeout);
    VS("LOADER [AppleEvent]: Handler sent \"%s\" message to child pid %ld.\n", descStr, (long)child_pid);

    /* In a onefile build, we may encounter a race condition between the parent
     * and the child process, because child_pid becomes valid immediately after
     * the process is forked, but the child process may not be able to receive
     * the events yet. In such cases, AESendMessage fails with procNotFound (-600).
     * To accommodate this situation,  we defer the event by storing its copy in our
     * event context structure, so that the caller can re-attempt to send it using
     * the pyi_apple_send_pending_event() function.
     */
    if (err == procNotFound) {
        VS("LOADER [AppleEvent]: Sending failed with procNotFound; storing the pending event...\n");

        err = AEDuplicateDesc(&childEvent, &_ae_ctx.pending_event);
        if (err == noErr) {
            _ae_ctx.retry_count = 0;
            _ae_ctx.has_pending_event = true;
        } else {
            VS("LOADER [AppleEvent]: Failed to copy the pending event: %d\n", (int)err);
            _ae_ctx.has_pending_event = false;
            _ae_ctx.retry_count = 0;
        }
    }

release_evt:
    free(buf);
    AEDisposeDesc(&childEvent);
release_desc:
    AEDisposeDesc(&target);
out:
    return err;
}

static Boolean realloc_checked(void **bufptr, Size size)
{
    void *tmp = realloc(*bufptr, size);
    if (!tmp) {
        OTHERERROR("LOADER [AppleEvents]: Failed to allocate a buffer of size %ld.\n", (long)size);
        return false;
    }
    VS("LOADER [AppleEvents]: (re)allocated a buffer of size %ld\n", (long)size);
    *bufptr = tmp;
    return true;
}

/* Handles apple events 'odoc' and 'GURL', both before and after the child_pid is up, Copying them to argv if child
 * not up yet, or otherwise forwarding them to the child if the child is started. */
static OSErr handle_odoc_GURL_events(const AppleEvent *theAppleEvent, const AEEventID evtID)
{
    const FourCharCode evtCode = (FourCharCode)evtID;
    const Boolean apple_event_is_open_doc = evtID == kAEOpenDocuments;
    const char *const descStr = apple_event_is_open_doc ? "OpenDoc" : "GetURL";

    VS("LOADER [AppleEvent]: %s handler called.\n", descStr);

    if (!pyi_utils_get_child_pid()) {
        /* Child process is not up yet -- so we pick up kAEOpen and/or kAEGetURL events and append them to argv. */

        AEDescList docList;
        OSErr err;
        long index;
        long count = 0;
        char *buf = NULL; /* Dynamic buffer for URL/file path data -- gets realloc'd as we iterate */

        VS("LOADER [AppleEvent ARGV_EMU]: Processing args for forward...\n");

        err = AEGetParamDesc(theAppleEvent, keyDirectObject, typeAEList, &docList);
        if (err != noErr) return err;

        err = AECountItems(&docList, &count);
        if (err != noErr) return err;

        for (index = 1; index <= count; ++index) /* AppleEvent lists are 1-indexed (I guess because of Pascal?) */
        {
            DescType returnedType;
            AEKeyword keywd;
            Size actualSize = 0, bufSize = 0;
            DescType typeCode = typeWildCard;

            err = AESizeOfNthItem(&docList, index, &typeCode, &bufSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: Failed to get size of Nth item %ld, error: %d\n",
                           index, (int)err);
                continue;
            }

            if (!realloc_checked((void **)&buf, bufSize+1)) {
                /* Not enough memory -- very unlikely but if so keep going */
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: Not enough memory for Nth item %ld, skipping%d\n", index);
                continue;
            }

            err = AEGetNthPtr(&docList, index, apple_event_is_open_doc ? typeFileURL : typeUTF8Text, &keywd,
                              &returnedType, buf, bufSize, &actualSize);
            if (err != noErr) {
                VS("LOADER [AppleEvent ARGV_EMU]: err[%ld] = %d\n", index-1L, (int)err);
            } else if (actualSize > bufSize) {
                /* This should never happen but is here for thoroughness */
                VS("LOADER [AppleEvent ARGV_EMU]: err[%ld]: not enough space in buffer (%ld > %ld)\n",
                   index-1L, (long)actualSize, (long)bufSize);
            } else {
                /* Copied data to buf, now ensure data is a simple file path and then append it to argv_pyi */
                char *tmp_str = NULL;
                Boolean ok;

                buf[actualSize] = 0; /* Ensure NUL-char termination. */
                if (apple_event_is_open_doc) {
                    /* Now, convert file:/// style URLs to an actual filesystem path for argv emu. */
                    CFURLRef url = CFURLCreateWithBytes(NULL, (UInt8 *)buf, actualSize, kCFStringEncodingUTF8,
                                                        NULL);
                    if (url) {
                        CFStringRef path = CFURLCopyFileSystemPath(url, kCFURLPOSIXPathStyle);
                        ok = false;
                        if (path) {
                            const Size newLen = (Size)CFStringGetMaximumSizeOfFileSystemRepresentation(path);
                            if (realloc_checked((void **)&buf, newLen+1)) {
                                bufSize = newLen;
                                ok = CFStringGetFileSystemRepresentation(path, buf, bufSize);
                                buf[bufSize] = 0; /* Ensure NUL termination */
                            }
                            CFRelease(path); /* free */
                        }
                        CFRelease(url); /* free */
                        if (!ok) {
                            VS("LOADER [AppleEvent ARGV_EMU]: "
                               "Failed to convert file:/// path to POSIX filesystem representation for arg %ld!\n",
                               index);
                            continue;
                        }
                    }
                }
                /* Append URL to argv_pyi array, reallocating as necessary */
                VS("LOADER [AppleEvent ARGV_EMU]: appending '%s' to argv_pyi\n", buf);
                if (pyi_utils_append_to_args(buf) < 0) {
                    OTHERERROR("LOADER [AppleEvent ARGV_EMU]: failed to append to argv_pyi: %s\n",
                               buf, strerror(errno));
                } else {
                    VS("LOADER [AppleEvent ARGV_EMU]: argv entry appended.\n");
                }
            }
        }

        free(buf); /* free of possible-NULL ok */

        err = AEDisposeDesc(&docList);

        return err;
    } /* else ... */

    /* The child process exists.. so we forward events to it */
    return generic_forward_apple_event(theAppleEvent,
                                       apple_event_is_open_doc ? kCoreEventClass : kInternetEventClass,
                                       evtID,
                                       descStr);
}

/* This brings the child process's windows to the foreground when the user double-clicks the
 * app's icon again in the macOS UI. 'rapp' is accepted by us only when the child is
 * already running. */
static OSErr handle_rapp_event(const AppleEvent *const theAppleEvent, const AEEventID evtID)
{
    OSErr err;

    VS("LOADER [AppleEvent]: ReopenApp handler called.\n");

    /* First, forward the 'rapp' event to the child */
    err = generic_forward_apple_event(theAppleEvent, kCoreEventClass, evtID, "ReopenApp");

    if (err == noErr) {
        /* Next, create a new activate ('actv') event. We never receive this event because
         * we have no window, but if we did this event would come next. So we synthesize an
         * event that should normally come for a windowed app, so that the child process
         * is brought to the foreground properly. */
        generic_forward_apple_event(NULL /* create new event with 0 params */,
                                    kAEMiscStandards, kAEActivate, "Activate");
    }

    return err;
}

/* Top-level event handler -- dispatches 'odoc', 'GURL', 'rapp', or 'actv' events. */
static pascal OSErr handle_apple_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    const FourCharCode evtCode = (FourCharCode)(intptr_t)handlerRefCon;
    const AEEventID evtID = (AEEventID)(intptr_t)handlerRefCon;
    (void)reply; /* unused */

    VS("LOADER [AppleEvent]: %s called with code '%s'.\n", __FUNCTION__, CC2Str(evtCode));

    switch(evtID) {
    case kAEOpenApplication:
        /* Nothing to do here, just make sure we report event as handled. */
        return noErr;
    case kAEOpenDocuments:
    case kAEGetURL:
        return handle_odoc_GURL_events(theAppleEvent, evtID);
    case kAEReopenApplication:
        return handle_rapp_event(theAppleEvent, evtID);
    case kAEActivate:
        /* This is not normally reached since the bootloader process lacks a window, and it
         * turns out macOS never sends this event to processes lacking a window. However,
         * since the Apple API docs are very sparse, this has been left-in here just in case. */
        return generic_forward_apple_event(theAppleEvent, kAEMiscStandards, evtID, "Activate");
    default:
        /* Not 'GURL', 'odoc', 'rapp', or 'actv'  -- this is not reached unless there is a
         * programming error in the code that sets up the handler(s) in pyi_process_apple_events. */
        OTHERERROR("LOADER [AppleEvent]: %s called with unexpected event type '%s'!\n",
                   __FUNCTION__, CC2Str(evtCode));
        return errAEEventNotHandled;
    }
}

/* This function gets installed as the process-wide UPP event handler.
 * It is responsible for dequeuing events and telling Carbon to forward
 * them to our installed handlers. */
static OSStatus evt_handler_proc(EventHandlerCallRef href, EventRef eref, void *data) {
    VS("LOADER [AppleEvent]: App event handler proc called.\n");
    Boolean release = false;
    EventRecord eventRecord;
    OSStatus err;

    /* Events of type kEventAppleEvent must be removed from the queue
     * before being passed to AEProcessAppleEvent. */
    if (IsEventInQueue(GetMainEventQueue(), eref)) {
        /* RemoveEventFromQueue will release the event, which will
         * destroy it if we don't retain it first. */
        VS("LOADER [AppleEvent]: Event was in queue, will release.\n");
        RetainEvent(eref);
        release = true;
        RemoveEventFromQueue(GetMainEventQueue(), eref);
    }
    /* Convert the event ref to the type AEProcessAppleEvent expects. */
    ConvertEventRefToEventRecord(eref, &eventRecord);
    VS("LOADER [AppleEvent]: what=%hu message=%lx ('%s') modifiers=%hu\n",
       eventRecord.what, eventRecord.message, CC2Str((FourCharCode)eventRecord.message), eventRecord.modifiers);
    /* This will end up calling one of the callback functions
     * that we installed in pyi_process_apple_events() */
    err = AEProcessAppleEvent(&eventRecord);
    if (err == errAEEventNotHandled) {
        VS("LOADER [AppleEvent]: Ignored event.\n");
    } else if (err != noErr) {
        VS("LOADER [AppleEvent]: Error processing event: %d\n", (int)err);
    }
    if (release) {
        ReleaseEvent(eref);
    }
    return noErr;
}


/*
 * Install Apple Event handlers. The handlers must be install prior to
 * calling pyi_apple_process_events().
 */
int pyi_apple_install_event_handlers()
{
    OSStatus err;

    /* Already installed; nothing to do */
    if (_ae_ctx.installed) {
        return 0;
    }

    VS("LOADER [AppleEvent]: Installing event handlers...\n");

    /* Allocate UPP (universal procedure pointer) for handler functions */
    _ae_ctx.upp_handler = NewEventHandlerUPP(evt_handler_proc);
    _ae_ctx.upp_handler_ae = NewAEEventHandlerUPP(handle_apple_event);

    /* Register Apple Event handlers */
    /* 'oapp' (open application) */
    err = AEInstallEventHandler(kCoreEventClass, kAEOpenApplication, _ae_ctx.upp_handler_ae, (SRefCon)kAEOpenApplication, false);
    if (err != noErr) {
        goto end;
    }
    /* 'odoc' (open document) */
    err = AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments, _ae_ctx.upp_handler_ae, (SRefCon)kAEOpenDocuments, false);
    if (err != noErr) {
        goto end;
    }
    /* 'GURL' (open url) */
    err = AEInstallEventHandler(kInternetEventClass, kAEGetURL, _ae_ctx.upp_handler_ae, (SRefCon)kAEGetURL, false);
    if (err != noErr) {
        goto end;
    }
    /* 'rapp' (re-open application) */
    err = AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, _ae_ctx.upp_handler_ae, (SRefCon)kAEReopenApplication, false);
    if (err != noErr) {
        goto end;
    }
    /* register 'actv' (activate) */
    err = AEInstallEventHandler(kAEMiscStandards, kAEActivate, _ae_ctx.upp_handler_ae, (SRefCon)kAEActivate, false);
    if (err != noErr) {
        goto end;
    }

    /* Install application event handler */
    err = InstallApplicationEventHandler(_ae_ctx.upp_handler, 1, event_types_ae, NULL, &_ae_ctx.handler_ref);

end:
    if (err != noErr) {
        /* Failed to install one of AE handlers or application event handler.
         * Remove everything. */
        AERemoveEventHandler(kAEMiscStandards, kAEActivate, _ae_ctx.upp_handler_ae, false);
        AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, _ae_ctx.upp_handler_ae, false);
        AERemoveEventHandler(kInternetEventClass, kAEGetURL, _ae_ctx.upp_handler_ae, false);
        AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, _ae_ctx.upp_handler_ae, false);
        AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, _ae_ctx.upp_handler_ae, false);

        DisposeEventHandlerUPP(_ae_ctx.upp_handler);
        DisposeAEEventHandlerUPP(_ae_ctx.upp_handler_ae);

        OTHERERROR("LOADER [AppleEvent]: Failed to install event handlers!\n");
        return -1;
    }

    VS("LOADER [AppleEvent]: Installed event handlers.\n");
    _ae_ctx.installed = true;
    return 0;
}

/*
 * Uninstall Apple Event handlers.
 */
int pyi_apple_uninstall_event_handlers()
{
    /* Not installed; nothing to do */
    if (!_ae_ctx.installed) {
        return 0;
    }

    VS("LOADER [AppleEvent]: Uninstalling event handlers...\n");

    /* Remove application event handler */
    RemoveEventHandler(_ae_ctx.handler_ref);
    _ae_ctx.handler_ref = NULL;

    /* Remove Apple Event handlers */
    AERemoveEventHandler(kAEMiscStandards, kAEActivate, _ae_ctx.upp_handler_ae, false);
    AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, _ae_ctx.upp_handler_ae, false);
    AERemoveEventHandler(kInternetEventClass, kAEGetURL, _ae_ctx.upp_handler_ae, false);
    AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, _ae_ctx.upp_handler_ae, false);
    AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, _ae_ctx.upp_handler_ae, false);

    /* Cleanup UPPs */
    DisposeEventHandlerUPP(_ae_ctx.upp_handler);
    DisposeAEEventHandlerUPP(_ae_ctx.upp_handler_ae);

    _ae_ctx.upp_handler = NULL;
    _ae_ctx.upp_handler_ae = NULL;

    _ae_ctx.installed = false;

    VS("LOADER [AppleEvent]: Uninstalled event handlers.\n");

    return 0;
}


/*
 * Apple event message pump; retrieves and processes Apple Events until
 * the specified timeout (in seconds) or an error is reached.
 */
void pyi_apple_process_events(float timeout)
{
    /* No-op if we failed to install event handlers */
    if (!_ae_ctx.installed) {
        return;
    }

    VS("LOADER [AppleEvent]: Processing Apple Events...\n");

    /* Event pump: process events until timeout (in seconds) or error */
    for (;;) {
        OSStatus status;
        EventRef event_ref; /* Event that caused ReceiveNextEvent to return. */

        /* If we have a pending event to forward, stop any further processing. */
        if (pyi_apple_has_pending_event()) {
            VS("LOADER [AppleEvent]: Breaking event loop due to pending event.\n");
            break;
        }

        VS("LOADER [AppleEvent]: Calling ReceiveNextEvent\n");
        status = ReceiveNextEvent(1, event_types_ae, timeout, kEventRemoveFromQueue, &event_ref);

        if (status == eventLoopTimedOutErr) {
            VS("LOADER [AppleEvent]: ReceiveNextEvent timed out\n");
            break;
        } else if (status != 0) {
            VS("LOADER [AppleEvent]: ReceiveNextEvent fetching events failed\n");
            break;
        } else {
            /* We actually pulled an event off the queue, so process it.
               We now 'own' the event_ref and must release it. */
            VS("LOADER [AppleEvent]: ReceiveNextEvent got an EVENT\n");

            VS("LOADER [AppleEvent]: Dispatching event...\n");
            status = SendEventToEventTarget(event_ref, GetEventDispatcherTarget());

            ReleaseEvent(event_ref);
            event_ref = NULL;
            if (status != 0) {
                VS("LOADER [AppleEvent]: processing events failed\n");
                break;
            }
        }
    }

    VS("LOADER [AppleEvent]: Out of the event loop.\n");
}


/*
 * Submit oapp (open application) event to ourselves. This is an attempt
 * to mitigate the issues with some UI frameworks (Tcl/Tk, in particular)
 * that are causes by argv-emu being enabled in onedir mode. In this case,
 * argv-emu swallows initial activation event (usually oapp; or odoc/GURL
 * if launched via file/url open request). This function attempts to
 * mitigate that by submitting a manual oapp event to itself so that the
 * UI framework finds the activation even in the event queue, as if no
 * Apple Event processing took place in the bootloader.
 */
void pyi_apple_submit_oapp_event()
{
    AppleEvent event = {typeNull, nil};
    AEAddressDesc target = {typeNull, nil};
    EventRef event_ref;
    ProcessSerialNumber psn;
    OSErr err;

    VS("LOADER [AppleEvent]: Submitting 'oapp' event...\n");

    // Get PSN via GetCurrentProcess. This function is deprecated, but
    // we cannot use {0, kCurrentProcess} because we need our event
    // to be queued.
#ifdef __clang__
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#endif
    err = GetCurrentProcess(&psn);
#ifdef __clang__
#pragma clang diagnostic pop
#endif
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to obtain PSN: %d\n", (int)err);
        goto cleanup;
    }

    // Create target address using the PSN, ...
    err = AECreateDesc(typeProcessSerialNumber, &psn, sizeof(psn), &target);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to create AEAddressDesc: %d\n", (int)err);
        goto cleanup;
    }

    // ... create OAPP event, ...
    err = AECreateAppleEvent(kCoreEventClass, kAEOpenApplication, &target, kAutoGenerateReturnID, kAnyTransactionID, &event);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to create OAPP event: %d\n", (int)err);
        goto cleanup;
    }

    // ... and send it
    err = AESendMessage(&event, NULL, kAENoReply, kAEDefaultTimeout);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to send event: %d\n", (int)err);
        goto cleanup;
    } else {
        VS("LOADER [AppleEvent]: Submitted 'oapp' event.\n");
    }

    // Now wait for the event to show up in event queue (this implicitly
    // assumes that no other activation event shows up, but those would
    // also solve the problem we are trying to mitigate).
    VS("LOADER [AppleEvent]: Waiting for 'oapp' event to show up in queue...\n");
    err = ReceiveNextEvent(1, event_types_ae, 10.0, kEventLeaveInQueue, &event_ref);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Timed out while waiting for submitted 'oapp' event to show up in queue!\n");
    } else {
        VS("LOADER [AppleEvent]: Submitted 'oapp' event is available in the queue.\n");
    }

cleanup:
    AEDisposeDesc(&event);
    AEDisposeDesc(&target);

    return;
}


/* Check if we have a pending event that we need to forward. */
int pyi_apple_has_pending_event()
{
    return _ae_ctx.has_pending_event;
}

/* Clean-up the pending event data and status. */
void pyi_apple_cleanup_pending_event()
{
    /* No-op if have no pending event. */
    if (!_ae_ctx.has_pending_event) {
        return;
    }

    /* Dispose event descriptor. */
    AEDisposeDesc(&_ae_ctx.pending_event);

    /* Cleanup state. */
    _ae_ctx.has_pending_event = false;
    _ae_ctx.retry_count = 0;
}

/* Attempt to re-send the pending event after the specified delay (in seconds). */
int pyi_apple_send_pending_event(float delay)
{
    OSErr err;

    /* No-op if have no pending event; signal success. */
    if (!_ae_ctx.has_pending_event) {
        return 0;
    }

    /* Sleep for the specified delay, then attempt to send the event. */
    _ae_ctx.retry_count++;
    VS("LOADER [AppleEvent]: Trying to forward pending event in %f second(s) (attempt %u)\n", delay, _ae_ctx.retry_count);
    usleep(delay*1000000);  /* sec to usec */
    err = AESendMessage(&_ae_ctx.pending_event, NULL, kAENoReply, kAEDefaultTimeout);

    /* If error is procNotFound (again), continue deferring the event. */
    if (err == procNotFound) {
        VS("LOADER [AppleEvent]: Sending failed with procNotFound; deferring event!\n");
        return 1;
    }

    /* Clean-up the pending event. */
    pyi_apple_cleanup_pending_event();

    /* Signal status. */
    if (err == noErr) {
        VS("LOADER [AppleEvent]: Successfully forwarded pending event\n");
        return 0;
    } else {
        VS("LOADER [AppleEvent]: Failed to forward pending event: %d\n", (int)err);
        return -1;
    }
}


#endif /* if defined(__APPLE__) && defined(WINDOWED) */
