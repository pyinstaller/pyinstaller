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

#if defined(__APPLE__) && defined(WINDOWED)

#include <Carbon/Carbon.h>  /* AppleEventsT */
#include <ApplicationServices/ApplicationServices.h> /* GetProcessForPID, etc */

#include "pyi_global.h"
#include "pyi_utils.h"


/* Not declared in modern headers but exists in Carbon libs since time immemorial
 * See: https://applescriptlibrary.files.wordpress.com/2013/11/apple-events-programming-guide.pdf */
extern Boolean ConvertEventRefToEventRecord(EventRef inEvent, EventRecord *outEvent);

/*
 * On Mac OS X this converts events from kAEOpenDocuments and kAEGetURL into sys.argv.
 * After startup, it also forwards kAEOpenDocuments and KAEGetURL events at runtime to the child process.
 *
 * TODO: The below can be simplified considerably if re-written in Objective C (e.g. put into pyi_utils_osx.m).
 */

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
    err = AESendMessage(&childEvent, NULL, kAENoReply, 60 /* 60 = about 1.0 seconds timeout */);
    VS("LOADER [AppleEvent]: Handler sent \"%s\" message to child pid %ld.\n", descStr, (long)child_pid);
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

/* Apple event message pump */
void pyi_process_apple_events(bool short_timeout)
{
    static EventHandlerUPP handler;
    static AEEventHandlerUPP handler_ae;
    static Boolean did_install = false;
    static EventHandlerRef handler_ref;
    EventTypeSpec event_types[1];  /*  List of event types to handle. */
    event_types[0].eventClass = kEventClassAppleEvent;
    event_types[0].eventKind = kEventAppleEvent;

    VS("LOADER [AppleEvent]: Processing...\n");

    if (!did_install) {
        OSStatus err;
        handler = NewEventHandlerUPP(evt_handler_proc);
        handler_ae = NewAEEventHandlerUPP(handle_apple_event);
        /* register 'odoc' (open document) */
        err = AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments, handler_ae, (SRefCon)kAEOpenDocuments, false);
        if (err == noErr) {
            /* register 'GURL' (open url) */
            err = AEInstallEventHandler(kInternetEventClass, kAEGetURL, handler_ae, (SRefCon)kAEGetURL, false);
        }
        if (err == noErr) {
            /* register 'rapp' (re-open application) */
            err = AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, handler_ae,
                                        (SRefCon)kAEReopenApplication, false);
        }
        if (err == noErr) {
            /* register 'actv' (activate) */
            err = AEInstallEventHandler(kAEMiscStandards, kAEActivate, handler_ae, (SRefCon)kAEActivate, false);
        }
        if (err == noErr) {
            err = InstallApplicationEventHandler(handler, 1, event_types, NULL, &handler_ref);
        }

        if (err != noErr) {
            /* App-wide handler failed. Uninstall everything. */
            AERemoveEventHandler(kAEMiscStandards, kAEActivate, handler_ae, false);
            AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, handler_ae, false);
            AERemoveEventHandler(kInternetEventClass, kAEGetURL, handler_ae, false);
            AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, handler_ae, false);
            DisposeEventHandlerUPP(handler);
            DisposeAEEventHandlerUPP(handler_ae);
            VS("LOADER [AppleEvent]: Disposed handlers.\n");
        } else {
            VS("LOADER [AppleEvent]: Installed handlers.\n");
            did_install = true;
        }
    }

    if (did_install) {
        /* Event pump: Process events for up to 1.0 (or 0.25) seconds (or until an error is encountered) */
        const EventTimeout timeout = short_timeout ? 0.25 : 1.0; /* number of seconds */
        for (;;) {
            OSStatus status;
            EventRef event_ref; /* Event that caused ReceiveNextEvent to return. */

            VS("LOADER [AppleEvent]: Calling ReceiveNextEvent\n");

            status = ReceiveNextEvent(1, event_types, timeout, kEventRemoveFromQueue, &event_ref);

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

    } else {
        static Boolean once = false;
        if (!once) {
            /* Log this only once since this is compiled-in even in non-debug mode and we
             * want to avoid console spam, since pyi_process_apple_events may be called a lot. */
            OTHERERROR("LOADER [AppleEvent]: ERROR installing handler.\n");
            once = true;
        }
    }
}

#endif /* if defined(__APPLE__) && defined(WINDOWED) */
