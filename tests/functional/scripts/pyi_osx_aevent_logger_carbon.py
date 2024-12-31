#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# This is a CLI-based AppleEvent logger application, intended for testing argv emulation and AppleEvent forwarding in
# PyInstaller-generated macOS .app bundles.

import os
import sys
import time
import json
import ctypes
import struct


# The ctypes-based bindings for Carbon API are taken from py2app's argv_emulation.py
class AEDesc(ctypes.Structure):
    _fields_ = [
        ("descKey", ctypes.c_int),
        ("descContent", ctypes.c_void_p),
    ]


class EventTypeSpec(ctypes.Structure):
    _fields_ = [
        ("eventClass", ctypes.c_int),
        ("eventKind", ctypes.c_uint),
    ]


def _ctypes_setup():
    carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")

    ae_callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    carbon.AEInstallEventHandler.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ae_callback,
        ctypes.c_void_p,
        ctypes.c_char,
    ]
    carbon.AERemoveEventHandler.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ae_callback,
        ctypes.c_char,
    ]

    carbon.AEProcessEvent.restype = ctypes.c_int
    carbon.AEProcessEvent.argtypes = [ctypes.c_void_p]

    carbon.ReceiveNextEvent.restype = ctypes.c_int
    carbon.ReceiveNextEvent.argtypes = [
        ctypes.c_long,
        ctypes.POINTER(EventTypeSpec),
        ctypes.c_double,
        ctypes.c_char,
        ctypes.POINTER(ctypes.c_void_p),
    ]

    carbon.AEGetParamDesc.restype = ctypes.c_int
    carbon.AEGetParamDesc.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(AEDesc),
    ]

    carbon.AECountItems.restype = ctypes.c_int
    carbon.AECountItems.argtypes = [
        ctypes.POINTER(AEDesc),
        ctypes.POINTER(ctypes.c_long),
    ]

    carbon.AEGetNthDesc.restype = ctypes.c_int
    carbon.AEGetNthDesc.argtypes = [
        ctypes.c_void_p,
        ctypes.c_long,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]

    carbon.AEGetDescDataSize.restype = ctypes.c_int
    carbon.AEGetDescDataSize.argtypes = [ctypes.POINTER(AEDesc)]

    carbon.AEGetDescData.restype = ctypes.c_int
    carbon.AEGetDescData.argtypes = [
        ctypes.POINTER(AEDesc),
        ctypes.c_void_p,
        ctypes.c_int,
    ]

    carbon.FSRefMakePath.restype = ctypes.c_int
    carbon.FSRefMakePath.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]

    return carbon


# Initialize Carbon bindings
carbon = _ctypes_setup()

kAEInternetSuite, = struct.unpack(">i", b"GURL")
kAEGetURL, = struct.unpack(">i", b"GURL")
kCoreEventClass, = struct.unpack(">i", b"aevt")
kAEOpenApplication, = struct.unpack(">i", b"oapp")
kAEReOpenApplication, = struct.unpack(">i", b"rapp")
kAEActivate, = struct.unpack(">i", b"actv")
kAEOpenDocuments, = struct.unpack(">i", b"odoc")
keyDirectObject, = struct.unpack(">i", b"----")
typeAEList, = struct.unpack(">i", b"list")
typeChar, = struct.unpack(">i", b"TEXT")
typeFSRef, = struct.unpack(">i", b"fsrf")
FALSE = b"\0"
TRUE = b"\1"
eventLoopTimedOutErr = -9875

kEventClassAppleEvent, = struct.unpack(">i", b"eppc")
kEventAppleEvent = 1

ae_callback = carbon.AEInstallEventHandler.argtypes[2]


# Application
class Application:
    def __init__(self):
        # Get runtime from command-line (first and only positional argument; filter our -psn_*** if it is present).
        self.runtime = 15
        filtered_args = [arg for arg in sys.argv[1:] if not arg.startswith('-psn')]
        if filtered_args:
            try:
                self.runtime = float(filtered_args[0])
            except Exception:
                pass

        # Track activations
        self.activation_count = 0

        # Open events log
        self.logfile = open(self._get_logfile_path(), 'w')

        # Event handlers map
        self.ae_handlers = {
            'oapp': self.open_app_handler,
            'odoc': self.open_document_handler,
            'GURL': self.open_url_handler,
            'rapp': self.reopen_app_handler,
            'actv': self.activate_app_handler,
        }

    def _get_logfile_path(self):
        # Open log file
        if getattr(sys, 'frozen', False):
            basedir = os.path.dirname(sys.executable)
            # Handle .app bundle
            if os.path.basename(basedir) == 'MacOS':
                basedir = os.path.abspath(os.path.join(basedir, os.pardir, os.pardir, os.pardir))
        else:
            basedir = os.path.dirname(__file__)

        return os.path.join(basedir, 'events.log')

    def log_error(self, message):
        self.logfile.write(f"ERROR {message}\n")
        self.logfile.flush()

    def log_event(self, event_id, event_data={}):
        self.logfile.write(f"{event_id} {json.dumps(event_data)}\n")
        self.logfile.flush()

    def main(self):
        # Log application start.
        self.log_event("started", {'args': sys.argv[1:]})

        # Configure AppleEvent handlers.
        @ae_callback
        def _ae_handler(message, reply, refcon):
            event_id = struct.pack(">i", refcon).decode('utf8')
            print("Event handler called with event ID: %s" % (event_id,))
            try:
                handler = self.ae_handlers.get(event_id, None)
                assert handler, "No handler available!"
                event_data = handler(message, reply, refcon)
                self.log_event(f"ae {event_id}", event_data)
            except Exception as e:
                print("Failed to handle event %s: %s!" % (event_id, e))
                self.log_error(f"Failed to handle event '{event_id}': {e}")

            return 0

        carbon.AEInstallEventHandler(kCoreEventClass, kAEOpenApplication, _ae_handler, kAEOpenApplication, FALSE)
        carbon.AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments, _ae_handler, kAEOpenDocuments, FALSE)
        carbon.AEInstallEventHandler(kAEInternetSuite, kAEGetURL, _ae_handler, kAEGetURL, FALSE)
        carbon.AEInstallEventHandler(kCoreEventClass, kAEReOpenApplication, _ae_handler, kAEReOpenApplication, FALSE)
        carbon.AEInstallEventHandler(kCoreEventClass, kAEActivate, _ae_handler, kAEActivate, FALSE)

        # Run the main loop and process events.
        start = time.time()

        eventType = EventTypeSpec()
        eventType.eventClass = kEventClassAppleEvent
        eventType.eventKind = kEventAppleEvent

        while time.time() < start + self.runtime:
            event = ctypes.c_void_p()
            status = carbon.ReceiveNextEvent(
                1,
                ctypes.byref(eventType),
                max(start + self.runtime - time.time(), 0),
                TRUE,
                ctypes.byref(event),
            )

            if status == eventLoopTimedOutErr:
                break
            elif status != 0:
                self.log_error(f"Failed to fetch events: {status}!")
                break

            status = carbon.AEProcessEvent(event)
            if status != 0:
                self.log_error(f"Failed to process event: {status}!")
                break

        # Cleanup
        carbon.AERemoveEventHandler(kCoreEventClass, kAEOpenApplication, _ae_handler, FALSE)
        carbon.AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, _ae_handler, FALSE)
        carbon.AERemoveEventHandler(kAEInternetSuite, kAEGetURL, _ae_handler, FALSE)
        carbon.AERemoveEventHandler(kCoreEventClass, kAEReOpenApplication, _ae_handler, FALSE)
        carbon.AERemoveEventHandler(kCoreEventClass, kAEActivate, _ae_handler, FALSE)

        # Log application finish.
        self.log_event("finished", {'activation_count': self.activation_count})

        self.logfile.close()
        self.logfile = None

    # *** Event handlers ***
    def open_app_handler(self, message, reply, refcon):
        # Nothing to do here, return empty dict.
        self.activation_count += 1
        return {}

    def reopen_app_handler(self, message, reply, refcon):
        # Increment the counter, return empty dict.
        self.activation_count += 1
        return {}

    def activate_app_handler(self, message, reply, refcon):
        # Increment the counter, return empty dict.
        self.activation_count += 1
        return {}

    def open_document_handler(self, message, reply, refcon):
        # Get descriptor list.
        listdesc = AEDesc()
        status = carbon.AEGetParamDesc(message, keyDirectObject, typeAEList, ctypes.byref(listdesc))
        assert status == 0, f'Could not retrieve descriptor list: {status}!'

        # Count items.
        item_count = ctypes.c_long()
        status = carbon.AECountItems(ctypes.byref(listdesc), ctypes.byref(item_count))
        assert status == 0, f'Could not count number of items in descriptor list: {status}!'

        # Collect data from all descriptors.
        desc = AEDesc()
        paths = []
        for i in range(item_count.value):
            # Retrieve descriptor.
            status = carbon.AEGetNthDesc(ctypes.byref(listdesc), i + 1, typeFSRef, 0, ctypes.byref(desc))
            assert status == 0, f'Could not retrieve descriptor #{i}: {status}!'

            # Get data.
            sz = carbon.AEGetDescDataSize(ctypes.byref(desc))
            buf = ctypes.create_string_buffer(sz)
            status = carbon.AEGetDescData(ctypes.byref(desc), buf, sz)
            assert status == 0, f'Could not retrieve data for descriptor #{i}: {status}!'

            # Decode path.
            fsref = buf
            buf = ctypes.create_string_buffer(4096)
            status = carbon.FSRefMakePath(ctypes.byref(fsref), buf, 4095)
            assert status == 0, f'Could not convert data for descriptor #{i} to path: {status}!'

            # Append to output list.
            paths.append(buf.value.decode("utf-8"))

        return paths

    def open_url_handler(self, message, reply, refcon):
        # Get descriptor list.
        listdesc = AEDesc()
        status = carbon.AEGetParamDesc(message, keyDirectObject, typeAEList, ctypes.byref(listdesc))
        assert status == 0, f'Could not retrieve descriptor list: {status}!'

        # Count items.
        item_count = ctypes.c_long()
        status = carbon.AECountItems(ctypes.byref(listdesc), ctypes.byref(item_count))
        assert status == 0, f'Could not count number of items in descriptor list: {status}!'

        # Collect data from all descriptors.
        desc = AEDesc()
        urls = []
        for i in range(item_count.value):
            # Retrieve descriptor.
            status = carbon.AEGetNthDesc(ctypes.byref(listdesc), i + 1, typeChar, 0, ctypes.byref(desc))
            assert status == 0, f'Could not retrieve descriptor #{i}: {status}!'

            # Get data.
            sz = carbon.AEGetDescDataSize(ctypes.byref(desc))
            buf = ctypes.create_string_buffer(sz)
            status = carbon.AEGetDescData(ctypes.byref(desc), buf, sz)
            assert status == 0, f'Could not retrieve data for descriptor #{i}: {status}!'

            # Append to output list.
            urls.append(buf.value.decode("utf-8"))

        return urls


if __name__ == '__main__':
    app = Application()
    app.main()
