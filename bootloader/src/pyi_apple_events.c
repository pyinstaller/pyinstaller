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
 */

#if defined(__APPLE__) && defined(WINDOWED)

#include "pyi_global.h"
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_apple_events.h"


/* Not declared in modern headers but exists in Carbon libs since time immemorial
 * See: https://applescriptlibrary.files.wordpress.com/2013/11/apple-events-programming-guide.pdf */
extern Boolean ConvertEventRefToEventRecord(EventRef inEvent, EventRecord *outEvent);


/* Helper macro for printing character from FOURCC codes; intended for
 * use in print-formatting functions with %c%c%c%c format. */
#define _FOURCC_CHARS(code) \
    ((char)((FourCharCode)code >> 24) & 0xFF), \
    ((char)((FourCharCode)code >> 16) & 0xFF), \
    ((char)((FourCharCode)code >> 8) & 0xFF), \
    ((char)((FourCharCode)code) & 0xFF)


/* Generic event forwarder -- forwards an event destined for this process
 * to the child process, copying its param object, if any. Parameter
 * `theAppleEvent` may be NULL, in which case a new event is created with
 * the specified class and id (containing 0 params / no param object). */
static OSErr
generic_forward_apple_event(
    const AppleEvent *const theAppleEvent /* NULL ok */,
    const AEEventClass eventClass,
    const AEEventID evtID,
    const char *const descStr
)
{
    OSErr err;
    AppleEvent childEvent;
    AEAddressDesc target;
    DescType actualType = 0;
    DescType typeCode = typeWildCard;
    char *buf = NULL; /* dynamic buffer to hold copied event param data */
    Size bufSize = 0;
    Size actualSize = 0;
    pid_t child_pid;

    VS("LOADER [AppleEvent]: forwarder called for \"%s\".\n", descStr);

    child_pid = global_pyi_ctx->child_pid; /* Copy from PYI_CONTEXT */
    if (!child_pid) {
        /* Child not up yet -- there is no way to "forward" this before child started!. */
         VS("LOADER [AppleEvent]: child not up yet (child PID is 0)\n");
         return errAEEventNotHandled;
    }

    VS("LOADER [AppleEvent]: forwarding '%c%c%c%c' event.\n", _FOURCC_CHARS(evtID));
    err = AECreateDesc(typeKernelProcessID, &child_pid, sizeof(child_pid), &target);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: failed to create AEAddressDesc: %d\n", (int)err);
        goto out;
    }
    VS("LOADER [AppleEvent]: created AEAddressDesc.\n");
    err = AECreateAppleEvent(
        eventClass,
        evtID,
        &target,
        kAutoGenerateReturnID,
        kAnyTransactionID,
        &childEvent
    );
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: failed to create event copy: %d\n", (int)err);
        goto release_desc;
    }
    VS("LOADER [AppleEvent]: created AppleEvent instance for child process.\n");

    if (!theAppleEvent) {
        /* Calling code wants a new event created from scratch, we do so
         * here and it will have 0 params. Assumption: caller knows that
         * the event type in question normally has 0 params. */
        VS(
            "LOADER [AppleEvent]: new AppleEvent class: '%c%c%c%c' code: '%c%c%c%c'\n",
            _FOURCC_CHARS(eventClass),
            _FOURCC_CHARS(evtID)
        );
    } else {
        err = AESizeOfParam(theAppleEvent, keyDirectObject, &typeCode, &bufSize);
        if (err != noErr) {
            /* No params for this event */
            VS(
                "LOADER [AppleEvent]: failed to get size of param (error=%d) -- event '%c%c%c%c' may lack params.\n",
                (int)err,
                _FOURCC_CHARS(evtID)
            );
        } else  {
            /* This event has a param object, copy it. */
            VS("LOADER [AppleEvent]: event has param object of size: %ld\n", (long)bufSize);
            buf = malloc(bufSize);
            if (!buf) {
                /* Failed to allocate buffer! */
                OTHERERROR(
                    "LOADER [AppleEvent]: failed to allocate buffer of size %ld: %s\n",
                    (long)bufSize,
                    strerror(errno)
                );
                goto release_evt;
            }
            VS("LOADER [AppleEvent]: allocated buffer of size: %ld\n", (long)bufSize);

            VS("LOADER [AppleEvent]: retrieving param...\n");
            err = AEGetParamPtr(
                theAppleEvent,
                keyDirectObject,
                typeWildCard,
                &actualType,
                buf,
                bufSize,
                &actualSize
            );
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent]: failed to get param data.\n");
                goto release_evt;
            }

            if (actualSize > bufSize) {
                /* From reading the Apple API docs, this should never
                 * happen, but it pays to program defensively here. */
                OTHERERROR(
                    "LOADER [AppleEvent]: got param size=%ld > bufSize=%ld, error!\n",
                    (long)actualSize,
                    (long)bufSize
                );
                goto release_evt;
            }

            VS(
                "LOADER [AppleEvent]: got param type=%x ('%c%c%c%c') size=%ld\n",
                (UInt32)actualType,
                _FOURCC_CHARS(actualType),
                (long)actualSize
            );

            VS("LOADER [AppleEvent]: putting param.\n");
            err = AEPutParamPtr(&childEvent, keyDirectObject, actualType, buf, actualSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent]: failed to put param data.\n");
                goto release_evt;
            }
        }
    }

    VS("LOADER [AppleEvent]: sending message...\n");
    err = AESendMessage(&childEvent, NULL, kAENoReply, kAEDefaultTimeout);
    VS("LOADER [AppleEvent]: handler sent \"%s\" message to child pid %ld.\n", descStr, (long)child_pid);

    /* In a onefile build, we may encounter a race condition between the
     * parent and the child process, because child PID becomes valid
     * immediately after the process is forked, but the child process
     * may not be able to receive the events yet. In such cases,
     * AESendMessage fails with procNotFound (-600). To accommodate this
     * situation,  we defer the event by storing its copy in our event
     * context structure, so that the caller can re-attempt to send it
     * using the pyi_apple_send_pending_event() function. */
    if (err == procNotFound) {
        APPLE_EVENT_HANDLER_CONTEXT *ae_ctx = &global_pyi_ctx->ae_ctx;

        VS("LOADER [AppleEvent]: sending failed with procNotFound; storing the pending event...\n");

        err = AEDuplicateDesc(&childEvent, &ae_ctx->pending_event);
        if (err == noErr) {
            ae_ctx->retry_count = 0;
            ae_ctx->has_pending_event = true;
        } else {
            VS("LOADER [AppleEvent]: failed to copy the pending event: %d\n", (int)err);
            ae_ctx->has_pending_event = false;
            ae_ctx->retry_count = 0;
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

static Boolean
realloc_checked(void **bufptr, Size size)
{
    void *tmp = realloc(*bufptr, size);
    if (!tmp) {
        OTHERERROR("LOADER [AppleEvents]: failed to allocate a buffer of size %ld.\n", (long)size);
        return false;
    }
    VS("LOADER [AppleEvents]: (re)allocated a buffer of size %ld\n", (long)size);
    *bufptr = tmp;
    return true;
}

/* Handles apple events 'odoc' and 'GURL', both before and after the
 * child process is up; if child process is up, the event is forwarded
 * to it; otherwise, the event is converted and added to argv. */
static OSErr
handle_odoc_GURL_events(const AppleEvent *theAppleEvent, const AEEventID evtID)
{
    const FourCharCode evtCode = (FourCharCode)evtID;
    const Boolean apple_event_is_open_doc = evtID == kAEOpenDocuments;
    const char *const descStr = apple_event_is_open_doc ? "OpenDoc" : "GetURL";

    VS("LOADER [AppleEvent]: %s handler called.\n", descStr);

    if (global_pyi_ctx->child_pid == 0) {
        /* Child process is not up yet -- so we pick up kAEOpen and/or
         * kAEGetURL events and append them to argv. */
        AEDescList docList;
        OSErr err;
        long index;
        long count = 0;
        char *buf = NULL; /* Dynamically (re)allocated buffer for URL/file path entries */

        VS("LOADER [AppleEvent ARGV_EMU]: processing args for forward...\n");

        err = AEGetParamDesc(theAppleEvent, keyDirectObject, typeAEList, &docList);
        if (err != noErr) return err;

        err = AECountItems(&docList, &count);
        if (err != noErr) return err;

        /* AppleEvent lists are 1-indexed (I guess because of Pascal?) */
        for (index = 1; index <= count; ++index) {
            DescType returnedType;
            AEKeyword keywd;
            Size actualSize = 0;
            Size bufSize = 0;
            DescType typeCode = typeWildCard;

            err = AESizeOfNthItem(&docList, index, &typeCode, &bufSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: item #%ld: failed to retrieve item size, error code: %d\n", index, (int)err);
                continue;
            }

            if (!realloc_checked((void **)&buf, bufSize+1)) {
                /* Not enough memory -- very unlikely but if so keep going */
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: item #%ld: insufficient memory - skipping!\n", index);
                continue;
            }

            err = AEGetNthPtr(
                &docList,
                index,
                apple_event_is_open_doc ? typeFileURL : typeUTF8Text,
                &keywd,
                &returnedType,
                buf,
                bufSize,
                &actualSize
            );
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: item #%ld: failed to retrieve item, error code: %d\n", index, (int)err);
            } else if (actualSize > bufSize) {
                /* This should never happen but is here for thoroughness */
                OTHERERROR(
                    "LOADER [AppleEvent ARGV_EMU]: item #%ld: not enough space in buffer (%ld > %ld)\n",
                    index,
                    (long)actualSize,
                    (long)bufSize
                );
            } else {
                /* Copied data to buf, now ensure data is a simple file path and then append it to argv_pyi */
                char *tmp_str = NULL;
                Boolean ok;

                buf[actualSize] = 0; /* Ensure NUL-char termination. */
                if (apple_event_is_open_doc) {
                    /* Now, convert file:/// style URLs to an actual filesystem path for argv emu. */
                    CFURLRef url = CFURLCreateWithBytes
                        (NULL,
                        (UInt8 *)buf,
                        actualSize,
                        kCFStringEncodingUTF8,
                        NULL
                    );
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
                            OTHERERROR(
                                "LOADER [AppleEvent ARGV_EMU]: item #%ld: failed to convert file:/// path to POSIX filesystem representation!\n",
                               index
                            );
                            continue;
                        }
                    }
                }

                /* Append URL to argv_pyi array, reallocating as necessary */
                VS("LOADER [AppleEvent ARGV_EMU]: appending '%s' to argv_pyi\n", buf);
                if (pyi_utils_append_to_args(global_pyi_ctx, buf) < 0) {
                    OTHERERROR(
                        "LOADER [AppleEvent ARGV_EMU]: failed to append to argv_pyi: %s\n",
                        buf,
                        strerror(errno)
                    );
                } else {
                    VS("LOADER [AppleEvent ARGV_EMU]: argv entry appended.\n");
                }
            }
        }

        free(buf); /* free of possible-NULL ok */

        err = AEDisposeDesc(&docList);

        return err;
    } /* else ... */

    /* The child process exists.. so we forward event to it */
    return generic_forward_apple_event(
        theAppleEvent,
        apple_event_is_open_doc ? kCoreEventClass : kInternetEventClass,
        evtID,
        descStr
    );
}

/* This brings the child process's windows to the foreground when user
 * double-clicks the app's icon again in the macOS UI. 'rapp' is accepted
 * by us only when the child is already running. */
static OSErr
handle_rapp_event(const AppleEvent *const theAppleEvent, const AEEventID evtID)
{
    OSErr err;

    VS("LOADER [AppleEvent]: ReopenApp handler called.\n");

    /* First, forward the 'rapp' event to the child */
    err = generic_forward_apple_event(theAppleEvent, kCoreEventClass, evtID, "ReopenApp");

    if (err == noErr) {
        /* Next, create a new activate ('actv') event. We never receive
         * this event because we have no window, but if we did this event
         * would come next. So we synthesize an event that should normally
         * come for a windowed app, so that the child process is brought
         * to the foreground properly. */
        generic_forward_apple_event(
            NULL /* create new event with 0 params */,
            kAEMiscStandards,
            kAEActivate,
            "Activate"
        );
    }

    return err;
}

/* Top-level event handler -- dispatches 'odoc', 'GURL', 'rapp', or 'actv' events. */
static OSErr
handle_apple_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    const FourCharCode evtCode = (FourCharCode)(intptr_t)handlerRefCon;
    const AEEventID evtID = (AEEventID)(intptr_t)handlerRefCon;
    (void)reply; /* unused */

    VS("LOADER [AppleEvent]: %s called with code '%c%c%c%c'.\n", __FUNCTION__, _FOURCC_CHARS(evtCode));

    switch(evtID) {
        case kAEOpenApplication: {
            /* Nothing to do here, just make sure we report event as handled. */
            return noErr;
        }
        case kAEOpenDocuments:
        case kAEGetURL: {
            return handle_odoc_GURL_events(theAppleEvent, evtID);
        }
        case kAEReopenApplication: {
            return handle_rapp_event(theAppleEvent, evtID);
        }
        case kAEActivate: {
            /* This is not normally reached since the bootloader process
             * lacks a window, and it turns out macOS never sends this event
             * to processes lacking a window. However, since the Apple API
             * docs are very sparse, this has been left-in here just in case. */
            return generic_forward_apple_event(theAppleEvent, kAEMiscStandards, evtID, "Activate");
        }
        default: {
            /* Not 'GURL', 'odoc', 'rapp', or 'actv'  -- this is not reached
             * unless there is a programming error in the code that sets up
             * the handler(s) in pyi_process_apple_events. */
            OTHERERROR(
                "LOADER [AppleEvent]: %s called with unexpected event type '%c%c%c%c'!\n",
                __FUNCTION__,
                _FOURCC_CHARS(evtCode)
            );
            return errAEEventNotHandled;
        }
    }
}

/* This function gets installed as the process-wide UPP event handler.
 * It is responsible for dequeuing events and telling Carbon to forward
 * them to our installed handlers. */
static OSStatus
evt_handler_proc(EventHandlerCallRef href, EventRef eref, void *data)
{
    Boolean release = false;
    EventRecord eventRecord;
    OSStatus err;

    VS("LOADER [AppleEvent]: app event handler proc called.\n");

    /* Events of type kEventAppleEvent must be removed from the queue
     * before being passed to AEProcessAppleEvent. */
    if (IsEventInQueue(GetMainEventQueue(), eref)) {
        /* RemoveEventFromQueue will release the event, which will
         * destroy it if we don't retain it first. */
        VS("LOADER [AppleEvent]: event was in queue, will release.\n");
        RetainEvent(eref);
        release = true;
        RemoveEventFromQueue(GetMainEventQueue(), eref);
    }

    /* Convert the event ref to the type AEProcessAppleEvent expects. */
    ConvertEventRefToEventRecord(eref, &eventRecord);
    VS(
        "LOADER [AppleEvent]: what=%hu message=%lx ('%c%c%c%c') modifiers=%hu\n",
        eventRecord.what,
        eventRecord.message,
        _FOURCC_CHARS(eventRecord.message),
        eventRecord.modifiers
    );

    /* This will end up calling one of the callback functions
     * that we installed in pyi_process_apple_events() */
    err = AEProcessAppleEvent(&eventRecord);
    if (err == errAEEventNotHandled) {
        VS("LOADER [AppleEvent]: ignored event.\n");
    } else if (err != noErr) {
        VS("LOADER [AppleEvent]: error processing event: %d\n", (int)err);
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
int
pyi_apple_install_event_handlers(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
{
    OSStatus err;

    /* Already installed; nothing to do */
    if (ae_ctx->installed) {
        return 0;
    }

    /* Initialize the single entry of event_types field */
    ae_ctx->event_types[0].eventClass = kEventClassAppleEvent;
    ae_ctx->event_types[0].eventKind = kEventAppleEvent;

    VS("LOADER [AppleEvent]: installing event handlers...\n");

    /* Allocate UPP (universal procedure pointer) for handler functions */
    ae_ctx->upp_handler = NewEventHandlerUPP(evt_handler_proc);
    ae_ctx->upp_handler_ae = NewAEEventHandlerUPP(handle_apple_event);

    /* Register Apple Event handlers */
    /* 'oapp' (open application) */
    err = AEInstallEventHandler(kCoreEventClass, kAEOpenApplication, ae_ctx->upp_handler_ae, (SRefCon)kAEOpenApplication, false);
    if (err != noErr) {
        goto end;
    }
    /* 'odoc' (open document) */
    err = AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments, ae_ctx->upp_handler_ae, (SRefCon)kAEOpenDocuments, false);
    if (err != noErr) {
        goto end;
    }
    /* 'GURL' (open url) */
    err = AEInstallEventHandler(kInternetEventClass, kAEGetURL, ae_ctx->upp_handler_ae, (SRefCon)kAEGetURL, false);
    if (err != noErr) {
        goto end;
    }
    /* 'rapp' (re-open application) */
    err = AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, ae_ctx->upp_handler_ae, (SRefCon)kAEReopenApplication, false);
    if (err != noErr) {
        goto end;
    }
    /* register 'actv' (activate) */
    err = AEInstallEventHandler(kAEMiscStandards, kAEActivate, ae_ctx->upp_handler_ae, (SRefCon)kAEActivate, false);
    if (err != noErr) {
        goto end;
    }

    /* Install application event handler */
    err = InstallApplicationEventHandler(ae_ctx->upp_handler, 1, ae_ctx->event_types, NULL, &ae_ctx->handler_ref);

end:
    if (err != noErr) {
        /* Failed to install one of AE handlers or application event handler.
         * Remove everything. */
        AERemoveEventHandler(kAEMiscStandards, kAEActivate, ae_ctx->upp_handler_ae, false);
        AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, ae_ctx->upp_handler_ae, false);
        AERemoveEventHandler(kInternetEventClass, kAEGetURL, ae_ctx->upp_handler_ae, false);
        AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, ae_ctx->upp_handler_ae, false);
        AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, ae_ctx->upp_handler_ae, false);

        DisposeEventHandlerUPP(ae_ctx->upp_handler);
        DisposeAEEventHandlerUPP(ae_ctx->upp_handler_ae);

        OTHERERROR("LOADER [AppleEvent]: failed to install event handlers!\n");
        return -1;
    }

    VS("LOADER [AppleEvent]: installed event handlers.\n");
    ae_ctx->installed = true;
    return 0;
}

/*
 * Uninstall Apple Event handlers.
 */
int
pyi_apple_uninstall_event_handlers(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
{
    /* Not installed; nothing to do */
    if (!ae_ctx->installed) {
        return 0;
    }

    VS("LOADER [AppleEvent]: uninstalling event handlers...\n");

    /* Remove application event handler */
    RemoveEventHandler(ae_ctx->handler_ref);
    ae_ctx->handler_ref = NULL;

    /* Remove Apple Event handlers */
    AERemoveEventHandler(kAEMiscStandards, kAEActivate, ae_ctx->upp_handler_ae, false);
    AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, ae_ctx->upp_handler_ae, false);
    AERemoveEventHandler(kInternetEventClass, kAEGetURL, ae_ctx->upp_handler_ae, false);
    AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, ae_ctx->upp_handler_ae, false);
    AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, ae_ctx->upp_handler_ae, false);

    /* Cleanup UPPs */
    DisposeEventHandlerUPP(ae_ctx->upp_handler);
    DisposeAEEventHandlerUPP(ae_ctx->upp_handler_ae);

    ae_ctx->upp_handler = NULL;
    ae_ctx->upp_handler_ae = NULL;

    ae_ctx->installed = false;

    VS("LOADER [AppleEvent]: uninstalled event handlers.\n");

    return 0;
}


/*
 * Apple event message pump; retrieves and processes Apple Events until
 * the specified timeout (in seconds) or an error is reached.
 */
void
pyi_apple_process_events(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float timeout)
{
    /* No-op if we failed to install event handlers */
    if (!ae_ctx->installed) {
        return;
    }

    VS("LOADER [AppleEvent]: processing Apple Events...\n");

    /* Event pump: process events until timeout (in seconds) or error */
    for (;;) {
        OSStatus status;
        EventRef event_ref; /* Event that caused ReceiveNextEvent to return. */

        /* If we have a pending event to forward, stop any further processing. */
        if (pyi_apple_has_pending_event(ae_ctx)) {
            VS("LOADER [AppleEvent]: breaking event loop due to pending event.\n");
            break;
        }

        VS("LOADER [AppleEvent]: calling ReceiveNextEvent\n");
        status = ReceiveNextEvent(1, ae_ctx->event_types, timeout, kEventRemoveFromQueue, &event_ref);

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

            VS("LOADER [AppleEvent]: dispatching event...\n");
            status = SendEventToEventTarget(event_ref, GetEventDispatcherTarget());

            ReleaseEvent(event_ref);
            event_ref = NULL;
            if (status != 0) {
                VS("LOADER [AppleEvent]: processing events failed\n");
                break;
            }
        }
    }

    VS("LOADER [AppleEvent]: out of the event loop.\n");
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
void
pyi_apple_submit_oapp_event(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
{
    AppleEvent event = {typeNull, nil};
    AEAddressDesc target = {typeNull, nil};
    EventRef event_ref;
    ProcessSerialNumber psn;
    OSErr err;

    VS("LOADER [AppleEvent]: submitting 'oapp' event...\n");

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
        OTHERERROR("LOADER [AppleEvent]: failed to obtain PSN: %d\n", (int)err);
        goto cleanup;
    }

    // Create target address using the PSN, ...
    err = AECreateDesc(typeProcessSerialNumber, &psn, sizeof(psn), &target);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: failed to create AEAddressDesc: %d\n", (int)err);
        goto cleanup;
    }

    // ... create OAPP event, ...
    err = AECreateAppleEvent(kCoreEventClass, kAEOpenApplication, &target, kAutoGenerateReturnID, kAnyTransactionID, &event);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: failed to create OAPP event: %d\n", (int)err);
        goto cleanup;
    }

    // ... and send it
    err = AESendMessage(&event, NULL, kAENoReply, kAEDefaultTimeout);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: failed to send event: %d\n", (int)err);
        goto cleanup;
    } else {
        VS("LOADER [AppleEvent]: submitted 'oapp' event.\n");
    }

    // Now wait for the event to show up in event queue (this implicitly
    // assumes that no other activation event shows up, but those would
    // also solve the problem we are trying to mitigate).
    VS("LOADER [AppleEvent]: waiting for 'oapp' event to show up in queue...\n");
    err = ReceiveNextEvent(1, ae_ctx->event_types, 10.0, kEventLeaveInQueue, &event_ref);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: timed out while waiting for submitted 'oapp' event to show up in queue!\n");
    } else {
        VS("LOADER [AppleEvent]: submitted 'oapp' event is available in the queue.\n");
    }

cleanup:
    AEDisposeDesc(&event);
    AEDisposeDesc(&target);

    return;
}


/* Check if we have a pending event that we need to forward. */
int pyi_apple_has_pending_event(const APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
{
    return ae_ctx->has_pending_event;
}

/* Clean-up the pending event data and status. */
void
pyi_apple_cleanup_pending_event(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
{
    /* No-op if have no pending event. */
    if (!ae_ctx->has_pending_event) {
        return;
    }

    /* Dispose event descriptor. */
    AEDisposeDesc(&ae_ctx->pending_event);

    /* Cleanup state. */
    ae_ctx->has_pending_event = false;
    ae_ctx->retry_count = 0;
}

/* Attempt to re-send the pending event after the specified delay (in seconds). */
int
pyi_apple_send_pending_event(APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float delay)
{
    OSErr err;

    /* No-op if have no pending event; signal success. */
    if (!ae_ctx->has_pending_event) {
        return 0;
    }

    /* Sleep for the specified delay, then attempt to send the event. */
    ae_ctx->retry_count++;
    VS("LOADER [AppleEvent]: trying to forward pending event in %f second(s) (attempt %u)\n", delay, ae_ctx->retry_count);
    usleep(delay*1000000);  /* sec to usec */
    err = AESendMessage(&ae_ctx->pending_event, NULL, kAENoReply, kAEDefaultTimeout);

    /* If error is procNotFound (again), continue deferring the event. */
    if (err == procNotFound) {
        VS("LOADER [AppleEvent]: sending failed with procNotFound; deferring event!\n");
        return 1;
    }

    /* Clean-up the pending event. */
    pyi_apple_cleanup_pending_event(ae_ctx);

    /* Signal status. */
    if (err == noErr) {
        VS("LOADER [AppleEvent]: successfully forwarded pending event\n");
        return 0;
    } else {
        VS("LOADER [AppleEvent]: failed to forward pending event: %d\n", (int)err);
        return -1;
    }
}


#endif /* if defined(__APPLE__) && defined(WINDOWED) */
