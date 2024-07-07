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

/* Having a header included outside of the ifdef block prevents the compilation
 * unit from becoming empty, which is disallowed by pedantic ISO C. */
#include "pyi_global.h"

#if defined(__APPLE__) && defined(WINDOWED)

#include <Carbon/Carbon.h>

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


/* Context structure for keeping track of data. */
struct APPLE_EVENT_HANDLER_CONTEXT
{
    /* Event handlers for argv-emu / event forwarding */
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
};


/* Generic event forwarder -- forwards an event destined for this process
 * to the child process, copying its param object, if any. Parameter
 * `theAppleEvent` may be NULL, in which case a new event is created with
 * the specified class and id (containing 0 params / no param object). */
static OSErr
generic_forward_apple_event(
    const AppleEvent *const theAppleEvent /* NULL ok */,
    const AEEventClass eventClass,
    const AEEventID evtID,
    const char *const descStr,
    struct PYI_CONTEXT *pyi_ctx
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

    PYI_DEBUG("LOADER [AppleEvent]: forwarder called for \"%s\".\n", descStr);

    child_pid = pyi_ctx->child_pid; /* Copy from PYI_CONTEXT */
    if (!child_pid) {
        /* Child not up yet -- there is no way to "forward" this before child started!. */
         PYI_DEBUG("LOADER [AppleEvent]: child not up yet (child PID is 0)\n");
         return errAEEventNotHandled;
    }

    PYI_DEBUG("LOADER [AppleEvent]: forwarding '%c%c%c%c' event.\n", _FOURCC_CHARS(evtID));
    err = AECreateDesc(typeKernelProcessID, &child_pid, sizeof(child_pid), &target);
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: failed to create AEAddressDesc: %d\n", (int)err);
        goto out;
    }
    PYI_DEBUG("LOADER [AppleEvent]: created AEAddressDesc.\n");
    err = AECreateAppleEvent(
        eventClass,
        evtID,
        &target,
        kAutoGenerateReturnID,
        kAnyTransactionID,
        &childEvent
    );
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: failed to create event copy: %d\n", (int)err);
        goto release_desc;
    }
    PYI_DEBUG("LOADER [AppleEvent]: created AppleEvent instance for child process.\n");

    if (!theAppleEvent) {
        /* Calling code wants a new event created from scratch, we do so
         * here and it will have 0 params. Assumption: caller knows that
         * the event type in question normally has 0 params. */
        PYI_DEBUG(
            "LOADER [AppleEvent]: new AppleEvent class: '%c%c%c%c' code: '%c%c%c%c'\n",
            _FOURCC_CHARS(eventClass),
            _FOURCC_CHARS(evtID)
        );
    } else {
        err = AESizeOfParam(theAppleEvent, keyDirectObject, &typeCode, &bufSize);
        if (err != noErr) {
            /* No params for this event */
            PYI_DEBUG(
                "LOADER [AppleEvent]: failed to get size of param (error=%d) -- event '%c%c%c%c' may lack params.\n",
                (int)err,
                _FOURCC_CHARS(evtID)
            );
        } else  {
            /* This event has a param object, copy it. */
            PYI_DEBUG("LOADER [AppleEvent]: event has param object of size: %ld\n", (long)bufSize);
            buf = malloc(bufSize);
            if (!buf) {
                /* Failed to allocate buffer! */
                PYI_WARNING(
                    "LOADER [AppleEvent]: failed to allocate buffer of size %ld: %s\n",
                    (long)bufSize,
                    strerror(errno)
                );
                goto release_evt;
            }
            PYI_DEBUG("LOADER [AppleEvent]: allocated buffer of size: %ld\n", (long)bufSize);

            PYI_DEBUG("LOADER [AppleEvent]: retrieving param...\n");
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
                PYI_WARNING("LOADER [AppleEvent]: failed to get param data.\n");
                goto release_evt;
            }

            if (actualSize > bufSize) {
                /* From reading the Apple API docs, this should never
                 * happen, but it pays to program defensively here. */
                PYI_WARNING(
                    "LOADER [AppleEvent]: got param size=%ld > bufSize=%ld, error!\n",
                    (long)actualSize,
                    (long)bufSize
                );
                goto release_evt;
            }

            PYI_DEBUG(
                "LOADER [AppleEvent]: got param type=%x ('%c%c%c%c') size=%ld\n",
                (UInt32)actualType,
                _FOURCC_CHARS(actualType),
                (long)actualSize
            );

            PYI_DEBUG("LOADER [AppleEvent]: putting param.\n");
            err = AEPutParamPtr(&childEvent, keyDirectObject, actualType, buf, actualSize);
            if (err != noErr) {
                PYI_WARNING("LOADER [AppleEvent]: failed to put param data.\n");
                goto release_evt;
            }
        }
    }

    PYI_DEBUG("LOADER [AppleEvent]: sending message...\n");
    err = AESendMessage(&childEvent, NULL, kAENoReply, kAEDefaultTimeout);
    PYI_DEBUG("LOADER [AppleEvent]: handler sent \"%s\" message to child pid %ld.\n", descStr, (long)child_pid);

    /* In a onefile build, we may encounter a race condition between the
     * parent and the child process, because child PID becomes valid
     * immediately after the process is forked, but the child process
     * may not be able to receive the events yet. In such cases,
     * AESendMessage fails with procNotFound (-600). To accommodate this
     * situation,  we defer the event by storing its copy in our event
     * context structure, so that the caller can re-attempt to send it
     * using the pyi_apple_send_pending_event() function. */
    if (err == procNotFound) {
        struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx = pyi_ctx->ae_ctx;

        PYI_DEBUG("LOADER [AppleEvent]: sending failed with procNotFound; storing the pending event...\n");

        err = AEDuplicateDesc(&childEvent, &ae_ctx->pending_event);
        if (err == noErr) {
            ae_ctx->retry_count = 0;
            ae_ctx->has_pending_event = true;
        } else {
            PYI_DEBUG("LOADER [AppleEvent]: failed to copy the pending event: %d\n", (int)err);
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
        PYI_WARNING("LOADER [AppleEvents]: failed to allocate a buffer of size %ld.\n", (long)size);
        return false;
    }
    PYI_DEBUG("LOADER [AppleEvents]: (re)allocated a buffer of size %ld\n", (long)size);
    *bufptr = tmp;
    return true;
}

/* Converts 'odoc' or 'GURL' event into command-line arguments, and
 * appends them to argv array. */
static OSErr
convert_event_to_argv(const AppleEvent *theAppleEvent, const AEEventID evtID, struct PYI_CONTEXT *pyi_ctx)
{
    const Boolean is_odoc_event = evtID == kAEOpenDocuments; /* 'odoc' vs 'GURL' */
    AEDescList docList;
    OSErr err;
    long index;
    long count = 0;
    char *buf = NULL; /* Dynamically (re)allocated buffer for URL/file path entries */

    PYI_DEBUG("LOADER [AppleEvent ARGV_EMU]: converting %s event to command-line arguments...\n", is_odoc_event ? "OpenDoc" : "GetURL");

    /* Retrieve event parameters/arguments */
    err = AEGetParamDesc(theAppleEvent, keyDirectObject, typeAEList, &docList);
    if (err != noErr) {
        return err;
    }

    err = AECountItems(&docList, &count);
    if (err != noErr) {
        return err;
    }

    /* AppleEvent lists are 1-indexed (I guess because of Pascal?) */
    for (index = 1; index <= count; ++index) {
        DescType returnedType;
        AEKeyword keywd;
        Size actualSize = 0;
        Size bufSize = 0;
        DescType typeCode = typeWildCard;

        /* Query data length */
        err = AESizeOfNthItem(&docList, index, &typeCode, &bufSize);
        if (err != noErr) {
            PYI_WARNING("LOADER [AppleEvent ARGV_EMU]: item #%ld: failed to retrieve item size, error code: %d\n", index, (int)err);
            continue;
        }

        /* Reallocate the buffer to required size */
        if (!realloc_checked((void **)&buf, bufSize + 1)) {
            /* Not enough memory -- very unlikely but if so keep going */
            PYI_WARNING("LOADER [AppleEvent ARGV_EMU]: item #%ld: insufficient memory - skipping!\n", index);
            continue;
        }

        /* Copy data */
        err = AEGetNthPtr(
            &docList,
            index,
            is_odoc_event ? typeFileURL : typeUTF8Text,
            &keywd,
            &returnedType,
            buf,
            bufSize,
            &actualSize
        );

        if (err != noErr) {
            PYI_WARNING("LOADER [AppleEvent ARGV_EMU]: item #%ld: failed to retrieve item, error code: %d\n", index, (int)err);
        } else if (actualSize > bufSize) {
            /* This should never happen but is here for thoroughness */
            PYI_WARNING(
                "LOADER [AppleEvent ARGV_EMU]: item #%ld: not enough space in buffer (%ld > %ld)\n",
                index,
                (long)actualSize,
                (long)bufSize
            );
        } else {
            /* Data was successfully copied; NULL-terminate the string */
            buf[actualSize] = 0;

            /* If this is 'odoc' event, convert file:/// style URLs to
             * actual filesystem path */
            if (is_odoc_event) {
                /* Create URL from string */
                CFURLRef url = CFURLCreateWithBytes(
                    NULL,
                    (UInt8 *)buf,
                    actualSize,
                    kCFStringEncodingUTF8,
                    NULL
                );
                if (url) {
                    /* Convert URL to POSIX path */
                    CFStringRef path = CFURLCopyFileSystemPath(url, kCFURLPOSIXPathStyle);
                    Boolean ok = false;
                    if (path) {
                        const Size newLen = (Size)CFStringGetMaximumSizeOfFileSystemRepresentation(path);
                        if (realloc_checked((void **)&buf, newLen + 1)) {
                            bufSize = newLen;
                            ok = CFStringGetFileSystemRepresentation(path, buf, bufSize);
                            buf[bufSize] = 0; /* Ensure NULL termination */
                        }
                        CFRelease(path); /* free */
                    }
                    CFRelease(url); /* free */
                    if (!ok) {
                        PYI_WARNING(
                            "LOADER [AppleEvent ARGV_EMU]: item #%ld: failed to convert file:/// path to POSIX filesystem representation!\n",
                            index
                        );
                        continue;
                    }
                }
            }

            /* Append URL to argv_pyi array, reallocating as necessary */
            PYI_DEBUG("LOADER [AppleEvent ARGV_EMU]: appending '%s' to argv_pyi\n", buf);
            if (pyi_utils_append_to_args(pyi_ctx, buf) < 0) {
                PYI_WARNING(
                    "LOADER [AppleEvent ARGV_EMU]: failed to append to argv_pyi: %s\n",
                    buf,
                    strerror(errno)
                );
            } else {
                PYI_DEBUG("LOADER [AppleEvent ARGV_EMU]: argv entry appended.\n");
            }
        }
    }

    free(buf); /* free of possible-NULL ok */

    err = AEDisposeDesc(&docList);

    return err;
}


/* 'oapp' event handler
 *
 * Nothing to do here, just make sure we report event as handled.
 */
static OSErr
handle_oapp_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    (void)theAppleEvent; /* unused */
    (void)reply; /* unused */
    (void)handlerRefCon; /* unused */

    PYI_DEBUG("LOADER [AppleEvent]: %s called\n", __FUNCTION__);
    return noErr;
}

/* 'odoc' event handler */
static OSErr
handle_odoc_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    struct PYI_CONTEXT *pyi_ctx = (struct PYI_CONTEXT *)handlerRefCon;
    (void)reply; /* unused */

    PYI_DEBUG("LOADER [AppleEvent]: %s called\n", __FUNCTION__);

    /* If child process is running, forward the event */
    if (pyi_ctx->child_pid != 0) {
        return generic_forward_apple_event(
            theAppleEvent,
            kCoreEventClass,
            kAEOpenDocuments,
            "OpenDoc",
            pyi_ctx
        );
    }

    /* Otherwise, convert the event into command-line argument */
    return convert_event_to_argv(theAppleEvent, kAEOpenDocuments, pyi_ctx);
}

/* 'GURL' event handler */
static OSErr
handle_gurl_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    struct PYI_CONTEXT *pyi_ctx = (struct PYI_CONTEXT *)handlerRefCon;
    (void)reply; /* unused */

    PYI_DEBUG("LOADER [AppleEvent]: %s called\n", __FUNCTION__);

    /* If child process is running, forward the event */
    if (pyi_ctx->child_pid != 0) {
        return generic_forward_apple_event(
            theAppleEvent,
            kInternetEventClass,
            kAEGetURL,
            "GetURL",
            pyi_ctx
        );
    }

    /* Otherwise, convert the event into command-line argument */
    return convert_event_to_argv(theAppleEvent, kAEGetURL, pyi_ctx);
}

/* 'rapp' event handler
 *
 * This brings the child process's windows to the foreground when user
 * double-clicks the app's icon again in the macOS UI. 'rapp' is accepted
 * by us only when the child is already running.
 */
static OSErr
handle_rapp_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    OSErr err;
    struct PYI_CONTEXT *pyi_ctx = (struct PYI_CONTEXT *)handlerRefCon;
    (void)reply; /* unused */

    PYI_DEBUG("LOADER [AppleEvent]: %s called\n", __FUNCTION__);

    /* First, forward the 'rapp' event to the child */
    err = generic_forward_apple_event(
        theAppleEvent,
        kCoreEventClass,
        kAEReopenApplication,
        "ReopenApp",
        pyi_ctx
    );

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
            "Activate",
            pyi_ctx
        );
    }

    return err;

}

/* 'actv' event handler
 *
 * We should normally not receive this event, because the bootloader
 * process lacks a window, and macOS only sends this event to process
 * that has a window. However, since the Apple API docs are very sparse,
 * this has been left-in here just in case.
 */
static OSErr
handle_actv_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    struct PYI_CONTEXT *pyi_ctx = (struct PYI_CONTEXT *)handlerRefCon;
    (void)reply; /* unused */

    PYI_DEBUG("LOADER [AppleEvent]: %s called\n", __FUNCTION__);

    return generic_forward_apple_event(
        theAppleEvent,
        kAEMiscStandards,
        kAEActivate,
        "Activate",
        pyi_ctx
    );
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

    PYI_DEBUG("LOADER [AppleEvent]: app event handler proc called.\n");

    /* Events of type kEventAppleEvent must be removed from the queue
     * before being passed to AEProcessAppleEvent. */
    if (IsEventInQueue(GetMainEventQueue(), eref)) {
        /* RemoveEventFromQueue will release the event, which will
         * destroy it if we do not retain it first. */
        PYI_DEBUG("LOADER [AppleEvent]: event was in queue, will release.\n");
        RetainEvent(eref);
        release = true;
        RemoveEventFromQueue(GetMainEventQueue(), eref);
    }

    /* Convert the event ref to the type AEProcessAppleEvent expects. */
    ConvertEventRefToEventRecord(eref, &eventRecord);
    PYI_DEBUG(
        "LOADER [AppleEvent]: what=%hu message=%lx ('%c%c%c%c') modifiers=%hu\n",
        eventRecord.what,
        eventRecord.message,
        _FOURCC_CHARS(eventRecord.message),
        eventRecord.modifiers
    );

    /* This will end up calling one of the callback functions
     * that we installed in pyi_apple_install_event_handlers() */
    err = AEProcessAppleEvent(&eventRecord);
    if (err == noErr) {
        PYI_DEBUG("LOADER [AppleEvent]: event handled.\n");
    } else if (err == errAEEventNotHandled) {
        PYI_DEBUG("LOADER [AppleEvent]: ignored event.\n");
    } else {
        PYI_DEBUG("LOADER [AppleEvent]: error processing event: %d\n", (int)err);
    }

    if (release) {
        ReleaseEvent(eref);
    }

    return noErr;
}


/*
 * Install Apple Event handlers. The handlers must be installed prior to
 * calling pyi_apple_process_events().
 */
struct APPLE_EVENT_HANDLER_CONTEXT *
pyi_apple_install_event_handlers(struct PYI_CONTEXT *pyi_ctx)
{
    struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx;
    OSStatus err;

    PYI_DEBUG("LOADER [AppleEvent]: installing event handlers...\n");

    /* Allocate the context structure */
    ae_ctx = (struct APPLE_EVENT_HANDLER_CONTEXT *)calloc(1, sizeof(struct APPLE_EVENT_HANDLER_CONTEXT));
    if (ae_ctx == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for APPLE_EVENT_HANDLER_CONTEXT.\n");
        return NULL;
    }

    /* Initialize the single entry of event_types field */
    ae_ctx->event_types[0].eventClass = kEventClassAppleEvent;
    ae_ctx->event_types[0].eventKind = kEventAppleEvent;

    /* Allocate UPP (universal procedure pointer) for handler functions */
    ae_ctx->upp_handler = NewEventHandlerUPP(evt_handler_proc);

    ae_ctx->upp_handler_oapp = NewAEEventHandlerUPP(handle_oapp_event);
    ae_ctx->upp_handler_odoc = NewAEEventHandlerUPP(handle_odoc_event);
    ae_ctx->upp_handler_gurl = NewAEEventHandlerUPP(handle_gurl_event);
    ae_ctx->upp_handler_rapp = NewAEEventHandlerUPP(handle_rapp_event);
    ae_ctx->upp_handler_actv = NewAEEventHandlerUPP(handle_actv_event);

    /* Register Apple Event handlers */
    /* 'oapp' (open application) */
    err = AEInstallEventHandler(kCoreEventClass, kAEOpenApplication, ae_ctx->upp_handler_oapp, (SRefCon)pyi_ctx, false);
    if (err != noErr) {
        goto end;
    }
    /* 'odoc' (open document) */
    err = AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments, ae_ctx->upp_handler_odoc, (SRefCon)pyi_ctx, false);
    if (err != noErr) {
        goto end;
    }
    /* 'GURL' (open url) */
    err = AEInstallEventHandler(kInternetEventClass, kAEGetURL, ae_ctx->upp_handler_gurl, (SRefCon)pyi_ctx, false);
    if (err != noErr) {
        goto end;
    }
    /* 'rapp' (re-open application) */
    err = AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, ae_ctx->upp_handler_rapp, (SRefCon)pyi_ctx, false);
    if (err != noErr) {
        goto end;
    }
    /* 'actv' (activate) */
    err = AEInstallEventHandler(kAEMiscStandards, kAEActivate, ae_ctx->upp_handler_actv, (SRefCon)pyi_ctx, false);
    if (err != noErr) {
        goto end;
    }

    /* Install application event handler */
    err = InstallApplicationEventHandler(ae_ctx->upp_handler, 1, ae_ctx->event_types, (void *)pyi_ctx, &ae_ctx->handler_ref);

end:
    if (err != noErr) {
        /* Failed to install one of AE handlers or application event handler.
         * Remove everything. */
        AERemoveEventHandler(kAEMiscStandards, kAEActivate, ae_ctx->upp_handler_actv, false);
        AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, ae_ctx->upp_handler_rapp, false);
        AERemoveEventHandler(kInternetEventClass, kAEGetURL, ae_ctx->upp_handler_gurl, false);
        AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, ae_ctx->upp_handler_odoc, false);
        AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, ae_ctx->upp_handler_oapp, false);

        DisposeEventHandlerUPP(ae_ctx->upp_handler);
        DisposeAEEventHandlerUPP(ae_ctx->upp_handler_oapp);
        DisposeAEEventHandlerUPP(ae_ctx->upp_handler_odoc);
        DisposeAEEventHandlerUPP(ae_ctx->upp_handler_gurl);
        DisposeAEEventHandlerUPP(ae_ctx->upp_handler_rapp);
        DisposeAEEventHandlerUPP(ae_ctx->upp_handler_actv);

        free(ae_ctx);

        PYI_ERROR("LOADER [AppleEvent]: failed to install event handlers!\n");
        return NULL;
    }

    PYI_DEBUG("LOADER [AppleEvent]: installed event handlers.\n");

    return ae_ctx;
}

/*
 * Uninstall Apple Event handlers.
 */
void
pyi_apple_uninstall_event_handlers(struct APPLE_EVENT_HANDLER_CONTEXT **ae_ctx_ref)
{
    struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx = *ae_ctx_ref;

    *ae_ctx_ref = NULL;

    /* Context unavailable; nothing to do */
    if (ae_ctx == NULL) {
        return;
    }

    PYI_DEBUG("LOADER [AppleEvent]: uninstalling event handlers...\n");

    /* Remove application event handler */
    RemoveEventHandler(ae_ctx->handler_ref);

    /* Remove Apple Event handlers */
    AERemoveEventHandler(kAEMiscStandards, kAEActivate, ae_ctx->upp_handler_actv, false);
    AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, ae_ctx->upp_handler_rapp, false);
    AERemoveEventHandler(kInternetEventClass, kAEGetURL, ae_ctx->upp_handler_gurl, false);
    AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, ae_ctx->upp_handler_odoc, false);
    AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, ae_ctx->upp_handler_oapp, false);

    /* Cleanup UPPs */
    DisposeEventHandlerUPP(ae_ctx->upp_handler);
    DisposeAEEventHandlerUPP(ae_ctx->upp_handler_oapp);
    DisposeAEEventHandlerUPP(ae_ctx->upp_handler_odoc);
    DisposeAEEventHandlerUPP(ae_ctx->upp_handler_gurl);
    DisposeAEEventHandlerUPP(ae_ctx->upp_handler_rapp);
    DisposeAEEventHandlerUPP(ae_ctx->upp_handler_actv);

    /* Free the context structure */
    free(ae_ctx);

    PYI_DEBUG("LOADER [AppleEvent]: uninstalled event handlers.\n");
}


/*
 * Apple event message pump; retrieves and processes Apple Events until
 * the specified timeout (in seconds) or an error is reached.
 */
void
pyi_apple_process_events(struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float timeout)
{
    PYI_DEBUG("LOADER [AppleEvent]: processing Apple Events...\n");

    /* Event pump: process events until timeout (in seconds) or error */
    for (;;) {
        OSStatus status;
        EventRef event_ref; /* Event that caused ReceiveNextEvent to return. */

        /* If we have a pending event to forward, stop any further processing. */
        if (pyi_apple_has_pending_event(ae_ctx)) {
            PYI_DEBUG("LOADER [AppleEvent]: breaking event loop due to pending event.\n");
            break;
        }

        PYI_DEBUG("LOADER [AppleEvent]: calling ReceiveNextEvent\n");
        status = ReceiveNextEvent(1, ae_ctx->event_types, timeout, kEventRemoveFromQueue, &event_ref);

        if (status == eventLoopTimedOutErr) {
            PYI_DEBUG("LOADER [AppleEvent]: ReceiveNextEvent timed out\n");
            break;
        } else if (status != 0) {
            PYI_DEBUG("LOADER [AppleEvent]: ReceiveNextEvent fetching events failed\n");
            break;
        } else {
            /* We actually pulled an event off the queue, so process it.
               We now 'own' the event_ref and must release it. */
            PYI_DEBUG("LOADER [AppleEvent]: ReceiveNextEvent got an EVENT\n");

            PYI_DEBUG("LOADER [AppleEvent]: dispatching event...\n");
            status = SendEventToEventTarget(event_ref, GetEventDispatcherTarget());

            ReleaseEvent(event_ref);
            event_ref = NULL;
            if (status != 0) {
                PYI_DEBUG("LOADER [AppleEvent]: processing events failed\n");
                break;
            }
        }
    }

    PYI_DEBUG("LOADER [AppleEvent]: out of the event loop.\n");
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
pyi_apple_submit_oapp_event()
{
    AppleEvent event = {typeNull, nil};
    AEAddressDesc target = {typeNull, nil};
    EventRef event_ref;
    ProcessSerialNumber psn;
    OSErr err;

    EventTypeSpec event_types[1] = {
        {kEventClassAppleEvent, kEventAppleEvent}
    };

    PYI_DEBUG("LOADER [AppleEvent]: submitting 'oapp' event...\n");

    /* Get PSN via GetCurrentProcess. This function is deprecated, but
     * we cannot use {0, kCurrentProcess} because we need our event
     * to be queued. */
#ifdef __clang__
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#endif
    err = GetCurrentProcess(&psn);
#ifdef __clang__
#pragma clang diagnostic pop
#endif
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: failed to obtain PSN: %d\n", (int)err);
        goto cleanup;
    }

    /* Create target address using the PSN, ... */
    err = AECreateDesc(typeProcessSerialNumber, &psn, sizeof(psn), &target);
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: failed to create AEAddressDesc: %d\n", (int)err);
        goto cleanup;
    }

    /* ... create OAPP event, ... */
    err = AECreateAppleEvent(kCoreEventClass, kAEOpenApplication, &target, kAutoGenerateReturnID, kAnyTransactionID, &event);
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: failed to create OAPP event: %d\n", (int)err);
        goto cleanup;
    }

    /* ... and send it */
    err = AESendMessage(&event, NULL, kAENoReply, kAEDefaultTimeout);
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: failed to send event: %d\n", (int)err);
        goto cleanup;
    } else {
        PYI_DEBUG("LOADER [AppleEvent]: submitted 'oapp' event.\n");
    }

    /* Now wait for the event to show up in event queue (this implicitly
     * assumes that no other activation event shows up, but those would
     * also solve the problem we are trying to mitigate). */
    PYI_DEBUG("LOADER [AppleEvent]: waiting for 'oapp' event to show up in queue...\n");
    err = ReceiveNextEvent(1, event_types, 10.0, kEventLeaveInQueue, &event_ref);
    if (err != noErr) {
        PYI_WARNING("LOADER [AppleEvent]: timed out while waiting for submitted 'oapp' event to show up in queue!\n");
    } else {
        PYI_DEBUG("LOADER [AppleEvent]: submitted 'oapp' event is available in the queue.\n");
    }

cleanup:
    AEDisposeDesc(&event);
    AEDisposeDesc(&target);

    return;
}


/* Check if we have a pending event that we need to forward. */
int pyi_apple_has_pending_event(const struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
{
    return ae_ctx->has_pending_event;
}

/* Clean-up the pending event data and status. */
void
pyi_apple_cleanup_pending_event(struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx)
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
pyi_apple_send_pending_event(struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx, float delay)
{
    OSErr err;

    /* No-op if have no pending event; signal success. */
    if (!ae_ctx->has_pending_event) {
        return 0;
    }

    /* Sleep for the specified delay, then attempt to send the event. */
    ae_ctx->retry_count++;
    PYI_DEBUG("LOADER [AppleEvent]: trying to forward pending event in %f second(s) (attempt %u)\n", delay, ae_ctx->retry_count);
    usleep(delay*1000000);  /* sec to usec */
    err = AESendMessage(&ae_ctx->pending_event, NULL, kAENoReply, kAEDefaultTimeout);

    /* If error is procNotFound (again), continue deferring the event. */
    if (err == procNotFound) {
        PYI_DEBUG("LOADER [AppleEvent]: sending failed with procNotFound; deferring event!\n");
        return 1;
    }

    /* Clean-up the pending event. */
    pyi_apple_cleanup_pending_event(ae_ctx);

    /* Signal status. */
    if (err == noErr) {
        PYI_DEBUG("LOADER [AppleEvent]: successfully forwarded pending event\n");
        return 0;
    } else {
        PYI_DEBUG("LOADER [AppleEvent]: failed to forward pending event: %d\n", (int)err);
        return -1;
    }
}

#endif /* if defined(__APPLE__) && defined(WINDOWED) */
