/*
 * ****************************************************************************
 * Copyright (c) 2026, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#include <stdlib.h> /* calloc */

#include "pyi_splash.h"

#if !defined(_WIN32) && !defined(__APPLE__)

/* Dynamic bindings for Xlib: /usr/include/X11/Xlib.h */
typedef struct Display_ Display;
#define Bool int

PYI_EXT_FUNC_PROTO(Display *, XOpenDisplay, (char *))
PYI_EXT_FUNC_PROTO(int, XCloseDisplay, (Display *))
PYI_EXT_FUNC_PROTO(int, XDefaultScreen, (Display *))
PYI_EXT_FUNC_PROTO(int, XDisplayWidth, (Display *, int))
PYI_EXT_FUNC_PROTO(int, XDisplayHeight, (Display *, int))
PYI_EXT_FUNC_PROTO(void, XFree, (void *))

struct DYLIB_XLIB
{
    /* Shared library handles */
    pyi_dylib_t handle;

    /* Function pointers for imported functions */
    PYI_EXT_FUNC_ENTRY(XOpenDisplay)
    PYI_EXT_FUNC_ENTRY(XCloseDisplay)
    PYI_EXT_FUNC_ENTRY(XDefaultScreen)
    PYI_EXT_FUNC_ENTRY(XDisplayWidth)
    PYI_EXT_FUNC_ENTRY(XDisplayHeight)
    PYI_EXT_FUNC_ENTRY(XFree)
};

static void pyi_dylib_xlib_cleanup(struct DYLIB_XLIB **dylib_ref)
{
    struct DYLIB_XLIB *dylib = *dylib_ref;

    *dylib_ref = NULL;

    if (dylib == NULL) {
        return;
    }

    /* Unload the shared library */
    if (dylib->handle != NULL) {
        PYI_DEBUG("DYLIB: unloading Xlib shared library...\n");

        if (dlclose(dylib->handle) < 0) {
            PYI_DEBUG("DYLIB: failed to unload Xlib shared library!\n");
        } else {
            PYI_DEBUG("DYLIB: unloaded Xlib shared library.\n");
        }
    }

    /* Free the allocated structure */
    free(dylib);
}

static struct DYLIB_XLIB *pyi_dylib_xlib_load()
{
    struct DYLIB_XLIB *dylib;

#ifdef AIX
#ifdef AIX64
    const char *libname = "libX11.a(shr_64.o)"; /* 64-bit object in .a archive */
#else
    const char *libname = "libX11.a(shr4.o)"; /* 32-bit object in .a archive */
#endif
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL | RTLD_MEMBER;
#else
    const char *libname = "libX11.so.6";
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL;
#endif

    /* Allocate structure */
    dylib = (struct DYLIB_XLIB *)calloc(1, sizeof(struct DYLIB_XLIB));
    if (dylib == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for DYLIB_XLIB structure.\n");
        return NULL;
    }

    /* Load shared library */
    dylib->handle = dlopen(libname, dlopen_flags);
    if (dylib->handle == NULL) {
        PYI_ERROR("Failed to load Xlib shared library '%s': %s\n", libname, dlerror());
        goto cleanup;
    }
    PYI_DEBUG("DYLIB: loaded Xlib shared library.\n");

    /* Import functions/symbols */
    #define _IMPORT_FUNCTION(name) \
        PYI_EXT_FUNC_BIND(dylib->handle, name, dylib->name); \
        if (!dylib->name) { \
            PYI_ERROR("Failed to import symbol %s from Xlib shared library: %s\n", #name, dlerror()); \
            goto cleanup; \
        }

    _IMPORT_FUNCTION(XOpenDisplay)
    _IMPORT_FUNCTION(XCloseDisplay)
    _IMPORT_FUNCTION(XDefaultScreen)
    _IMPORT_FUNCTION(XDisplayWidth)
    _IMPORT_FUNCTION(XDisplayHeight)
    _IMPORT_FUNCTION(XFree)

    #undef _IMPORT_FUNCTION

    PYI_DEBUG("DYLIB: imported symbols from Xlib shared library.\n");

    return dylib;

cleanup:
    pyi_dylib_xlib_cleanup(&dylib);
    return dylib;
}

/* Dynamic bindings for Xinerama extension: /usr/include/X11/extensions/Xinerama.h */
typedef struct
{
   int screen_number;
   short x_org;
   short y_org;
   short width;
   short height;
} XineramaScreenInfo;

PYI_EXT_FUNC_PROTO(Bool, XineramaQueryExtension, (Display *, int *, int *))
PYI_EXT_FUNC_PROTO(XineramaScreenInfo *, XineramaQueryScreens, (Display *, int *))

struct DYLIB_XINERAMA
{
    /* Shared library handles */
    pyi_dylib_t handle;

    /* Function pointers for imported functions */
    PYI_EXT_FUNC_ENTRY(XineramaQueryExtension)
    PYI_EXT_FUNC_ENTRY(XineramaQueryScreens)
};

static void pyi_dylib_xinerama_cleanup(struct DYLIB_XINERAMA **dylib_ref)
{
    struct DYLIB_XINERAMA *dylib = *dylib_ref;

    *dylib_ref = NULL;

    if (dylib == NULL) {
        return;
    }

    /* Unload the shared library */
    if (dylib->handle != NULL) {
        PYI_DEBUG("DYLIB: unloading Xinerama shared library...\n");

        if (dlclose(dylib->handle) < 0) {
            PYI_DEBUG("DYLIB: failed to unload Xinerama shared library!\n");
        } else {
            PYI_DEBUG("DYLIB: unloaded Xinerama shared library.\n");
        }
    }

    /* Free the allocated structure */
    free(dylib);
}

static struct DYLIB_XINERAMA *pyi_dylib_xinerama_load()
{
    struct DYLIB_XINERAMA *dylib;

#ifdef AIX
    /* On AIX, the Xinerama extension is part of monolithic Xext
     * extension library. */
#ifdef AIX64
    const char *libname = "libXext.a(shr_64.o)"; /* 64-bit object in .a archive */
#else
    const char *libname = "libXext.a(shr.o)"; /* 32-bit object in .a archive */
#endif
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL | RTLD_MEMBER;
#else
    const char *libname = "libXinerama.so.1";
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL;
#endif

    /* Allocate structure */
    dylib = (struct DYLIB_XINERAMA *)calloc(1, sizeof(struct DYLIB_XINERAMA));
    if (dylib == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for DYLIB_XINERAMA structure.\n");
        return NULL;
    }

    /* Load shared library */
    dylib->handle = dlopen(libname, dlopen_flags);
    if (dylib->handle == NULL) {
        PYI_ERROR("Failed to load Xinerama shared library '%s': %s\n", libname, dlerror());
        goto cleanup;
    }
    PYI_DEBUG("DYLIB: loaded Xinerama shared library.\n");

    /* Import functions/symbols */
    #define _IMPORT_FUNCTION(name) \
        PYI_EXT_FUNC_BIND(dylib->handle, name, dylib->name); \
        if (!dylib->name) { \
            PYI_ERROR("Failed to import symbol %s from Xinerama shared library: %s\n", #name, dlerror()); \
            goto cleanup; \
        }

    _IMPORT_FUNCTION(XineramaQueryExtension)
    _IMPORT_FUNCTION(XineramaQueryScreens)

    #undef _IMPORT_FUNCTION

    PYI_DEBUG("DYLIB: imported symbols from Xinerama shared library.\n");

    return dylib;

cleanup:
    pyi_dylib_xinerama_cleanup(&dylib);
    return dylib;
}

/* Splash screen centering implementation for X11 / (X)Wayland */
int _pyi_splash_setup_centering_mode_x11(int mode, int *x, int *y, int *width, int *height)
{
    struct DYLIB_XLIB *xlib = NULL;
    struct DYLIB_XINERAMA *xinerama = NULL;

    Display *display = NULL;
    int screen = 0;

    int xinerama_event_base;
    int xinerama_error_base;
    XineramaScreenInfo *xinerama_screens = NULL;
    int num_xinerama_screens = 0;

    int status = -1;

    /* Load Xlib */
    PYI_DEBUG("SPLASH: loading Xlib shared library...\n");
    xlib = pyi_dylib_xlib_load();
    if (xlib == NULL) {
        PYI_DEBUG("SPLASH: could not dynamically load the Xlib shared library!\n");
        goto end;
    }

    /* Connect to display */
    display = xlib->XOpenDisplay(NULL);
    if (!display) {
        PYI_DEBUG("SPLASH: could not connect to display!\n");
        goto end;
    }

    /* Get screen number */
    screen = xlib->XDefaultScreen(display);

    /* We do not support "active screen" mode; we would require to query
     * mouse cursor position, and while XQueryPointer() exists in Xlib,
     * it does not work on contemporary (X)Wayland systems. For now,
     * just fall back to primary screen mode. */
    if (mode == SPLASH_CENTER_ACTIVE_SCREEN) {
        PYI_DEBUG("SPLASH: 'active' mode not supported on this platform - falling back to 'primary'!\n");
        mode = SPLASH_CENTER_PRIMARY_SCREEN;
    }

    /* For virtual screen, we can use XDisplayWidth() and XDisplayHeight() */
    if (mode == SPLASH_CENTER_VIRTUAL_SCREEN) {
        *x = 0;
        *y = 0;
        *width = xlib->XDisplayWidth(display, screen);
        *height = xlib->XDisplayHeight(display, screen);
        status = 0; /* Succeeded */
        goto end;
    }

    /* For primary-screen mode, we need to use Xinerama extension to query
     * extent of the primary screen/monitor (listed first in the output) */
    if (mode != SPLASH_CENTER_PRIMARY_SCREEN) {
        goto end;
    }

    PYI_DEBUG("SPLASH: loading Xinerama shared library...\n");
    xinerama = pyi_dylib_xinerama_load();
    if (!xinerama) {
        PYI_DEBUG("SPLASH: could not dynamically load the Xinerama shared library!\n");
        goto end;
    }
    if (!xinerama->XineramaQueryExtension(display, &xinerama_event_base, &xinerama_error_base)) {
        PYI_DEBUG("SPLASH: Xinerama extension is not available!\n");
        goto end;
    }

    xinerama_screens = xinerama->XineramaQueryScreens(display, &num_xinerama_screens);
    if (!num_xinerama_screens) {
        PYI_DEBUG("SPLASH: could not obtain screen info from Xinerama extension!\n");
        goto end;
    }

    *x = xinerama_screens[0].x_org;
    *y = xinerama_screens[0].y_org;
    *width = xinerama_screens[0].width;
    *height = xinerama_screens[0].height;
    status = 0; /* Succeeded */

    xlib->XFree(xinerama_screens);

end:
    /* Cleanup */
    if (display) {
        xlib->XCloseDisplay(display);
    }

    pyi_dylib_xlib_cleanup(&xlib);
    pyi_dylib_xinerama_cleanup(&xinerama);

    return status;
}

#endif
