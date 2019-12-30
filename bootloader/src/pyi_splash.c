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

#ifdef _WIN32
    #include <windows.h>
    #include <process.h>  /* _beginthread, _endthread */
    #include <winsock.h>  /* ntohl */
#else
    #include <stdlib.h>   /* malloc */
    #include <string.h>   /* strncmp, strcpy, strcat */
    #include <limits.h>   /* PATH_MAX */
#endif  /* _WIN32 */
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
 * The functions in this file are defined upside down
 * so that the platform-specific implementation is on top
 * and is not exposed to other parts of the bootloader.
 *****************************************************************/

#if defined(_WIN32)
/*
 * Windows platform-dependent implementation of the splash screen.
 *
 * Functions in this section should only be called using platform-independent functions
 * or by each other.
 */

    /* Window message for updating text */
    #define _WM_SPLASH             (WM_USER + 0xF)
    /* Window class name */
    #define _SPLASH_WINDOW_NAME    L"PyInstallerBootloaderSplash"

/* Windows application state.
 * This state should store all constant parameters required to
 * run the window */
typedef struct _window_state {
    /* Constant data */
    SIZE     wnd_size;
    POINT    wnd_origin;
    RECT     wnd_text_rect;
    COLORREF wnd_text_color;
    DWORD    wnd_blendmode;

    /* Handles to UI-related elements
     * All handles in this part needs to be deleted or
     * released before the struct gets freed */
    HFONT   wnd_font;
    HBITMAP splash_bitmap;
} SPLASHWINDOWSTATE;

/* Callback for enumerating through windows*/
BOOL CALLBACK
win32EnumWindowsProc(HWND hwnd, LPARAM lParam)
{
    DWORD processId;
    wchar_t class_name[32];

    /* Ask by which process the windows was created */
    GetWindowThreadProcessId(hwnd, &processId);

    if (processId == getpid()) {
        /* Get the class name of the current window */
        GetClassName(hwnd, class_name, 31);

        /* Only if the window is:
         *  1. Not a child window (like e.g. a dialog)
         *  2. Visible (not hidden by the OS)
         *  3. and the class name matches
         */
        if (GetWindow(hwnd, GW_OWNER) == 0
            && IsWindowVisible(hwnd)
            && wcsncmp(class_name,
                       _SPLASH_WINDOW_NAME,
                       wcslen(_SPLASH_WINDOW_NAME)) == 0) {
            *((HWND *) lParam) = hwnd;
            return FALSE;
        }
    }
    return TRUE;
}

/* Returns the current splash screen window */
static HWND
win32GetCurrentSplashWindow()
{
    HWND hwnd = NULL;

    /* Enumerate through all open windows to find the splash screen */
    EnumWindows(win32EnumWindowsProc, (LPARAM) &hwnd);

    return hwnd;
}

/* Extract the splash screen bitmap from SPLASH structure and return a handle. */
static HBITMAP
win32LoadBitmapHandle(SPLASH *splash)
{
    BITMAPINFO bitmapinfo = {0};
    HBITMAP splash_bitmap;
    char *pPixels = NULL;
    int lines_read;

    /* Create bitmap header for pixel data */
    bitmapinfo.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bitmapinfo.bmiHeader.biPlanes = 1;
    bitmapinfo.bmiHeader.biCompression = BI_RGB;
    bitmapinfo.bmiHeader.biWidth = ntohl(splash->img_width);
    bitmapinfo.bmiHeader.biHeight = ntohl(splash->img_height);
    bitmapinfo.bmiHeader.biBitCount = splash->img_bit_count;

    /* Create new bitmap and receive the handle */
    splash_bitmap = CreateDIBSection(NULL,
                                     &bitmapinfo,
                                     DIB_RGB_COLORS,
                                     (void **) &pPixels,
                                     NULL,
                                     0);

    /* Check if everything went alright */
    if (splash_bitmap == NULL || splash_bitmap == INVALID_HANDLE_VALUE) {
        FATAL_WINERROR("CreateDIBSection",
                       "Could not create DIB section for splash screen.\n");
        return NULL;
    }

    /* Copy the bitmap from splash into the new bitmap */
    lines_read = SetDIBits(NULL,
                           splash_bitmap,
                           0,
                           ntohl(splash->img_height),
                           &splash->bitmap,
                           &bitmapinfo,
                           DIB_RGB_COLORS);

    if (lines_read != ntohl(splash->img_height)) {
        FATAL_WINERROR("SetDIBits",
                       "Could not copy all %d lines, but only %d.\n",
                       ntohl(splash->img_height),
                       lines_read);
        return NULL;
    }

    return splash_bitmap;
}

/* Draw/Create a bitmap which can be used for displaying as the
 * splash screen.
 *
 * The returned bitmap is a 32 bit image.
 */
static HBITMAP
win32HandleText(SPLASHWINDOWSTATE *pState, HDC hdc_screen, char *text_msg)
{
    RECT text_rect;
    HFONT old_font;
    HBITMAP hbitmap_text;
    HDC hdc_text, hdc_image;
    HBITMAP old_image, old_text;
    wchar_t *wtext_msg;
    RGBQUAD *tmp, *pBits = NULL;
    BITMAPINFOHEADER bitmapinfo = {0};
    int x, y, idx;
    int rect_width, rect_height;
    char *alpha_channel;

    /* Translate string to UTF16 for usage with win32 API */
    wtext_msg = pyi_win32_utils_from_utf8(NULL, text_msg, 0);

    /* Copy rectangle for the text */
    CopyRect(&text_rect, &pState->wnd_text_rect);

    /*
     * If we want to display text on the splash screen,
     * it gets a little more complicated. Windows does not send WM_PAINT messages
     * to the window, so it has to take care of its own appearance.
     */
    hdc_image = CreateCompatibleDC(NULL);
    old_image = (HBITMAP) SelectObject(hdc_image, pState->splash_bitmap);

    /* Create new bitmap with hdc for the image with text */
    hdc_text = CreateCompatibleDC(NULL);

    bitmapinfo.biSize = sizeof(bitmapinfo);
    bitmapinfo.biWidth = pState->wnd_size.cx;
    bitmapinfo.biHeight = pState->wnd_size.cy;
    bitmapinfo.biPlanes = 1;
    bitmapinfo.biBitCount = 32;

    hbitmap_text = CreateDIBSection(hdc_screen,
                                    (BITMAPINFO *) &bitmapinfo,
                                    DIB_RGB_COLORS,
                                    (void **) &pBits,
                                    NULL,
                                    0);
    old_text = (HBITMAP) SelectObject(hdc_text, hbitmap_text);

    /*
     * Copy over the bitmap from the original splash screen.
     *
     * If we paint on the original DC with DrawText, it will affect the original
     * pixel data, so we have to make a copy of the original data so that
     * the text on the splash screen doesn't overlap on multiple calls.
     */
    if (!BitBlt(hdc_text,
                0, 0,
                pState->wnd_size.cx, pState->wnd_size.cy,
                hdc_image,
                0, 0,
                SRCCOPY)) {
        FATAL_WINERROR("BitBlt", "Cannot copy from %d to %d\n", hdc_image, hdc_text);
    }

    /* Prepare the text style */
    SetBkMode(hdc_text, TRANSPARENT);
    SetTextColor(hdc_text, ntohl(pState->wnd_text_color));
    old_font = (HFONT) SelectObject(hdc_text, pState->wnd_font);

    /** WORKAROUND
     * DrawText does not work well with 32bit images, since it sets the alpha
     * value of the rect it modifies to 0x00 (=transparent), but the R-, G- and
     * B-channel are changed.
     *
     * To restore the transparency values of the pixels inside the rectangle, a
     * copy of the alpha channel is made before writing text to the bitmap. After
     * the text is written, the alpha channel of the rectangle is restored.
     *
     * One cannot assume, that every pixel of 0x00000000 is black, since
     * transparent pixels do have the same color value.
     */

    /* Modify text_rect to fit the text and decrease the amount
     * of pixels the loops to restore the alpha channel need to process */
    DrawText(hdc_text,
             wtext_msg,
             -1,
             &text_rect,
             DT_TOP | DT_LEFT | DT_CALCRECT);

    /* Calculate the dimensions of the rect */
    rect_height = text_rect.bottom - text_rect.top;
    rect_width = text_rect.right - text_rect.left;

    /* Iterate through the pixels inside the text_rect and copy their alpha
     * value into the new buffer. */
    alpha_channel = (char *) calloc(rect_height * rect_width, sizeof(char));

    for (y = 0; y < rect_height; ++y) {
        for (x = 0; x < rect_width; ++x) {
            /* idx: array index of the RGBQUAD inside the bitmap color buffer */
            idx = (bitmapinfo.biHeight - text_rect.bottom + y) * bitmapinfo.biWidth +
                  text_rect.left + x;

            /* The text_rect can include regions outside the bitmap, so check
             * if idx is a valid index */
            if (0x00 <= idx && idx <= (bitmapinfo.biWidth * bitmapinfo.biHeight)) {
                alpha_channel[y * rect_width + x] = pBits[idx].rgbReserved;
            }
        }
    }

    /* Draw the text onto the image. */
    if (!DrawText(hdc_text,
                  wtext_msg,
                  -1,
                  &text_rect,
                  DT_TOP | DT_LEFT)) {
        FATAL_WINERROR("DrawText", "Cannot draw \"%ls\" onto %d\n", hdc_text, wtext_msg);
    }

    /* To restore the alpha channel of each pixel iterate through the text_rect
     * and restore their original value */
    for (y = 0; y < rect_height; ++y) {
        for (x = 0; x < rect_width; ++x) {
            idx = (bitmapinfo.biHeight - text_rect.bottom + y) * bitmapinfo.biWidth +
                  text_rect.left + x;
            tmp = &pBits[idx];

            if (0x00 <= idx && idx <= (bitmapinfo.biWidth * bitmapinfo.biHeight)) {
                if (tmp->rgbReserved == 0x00 && *((DWORD *) (tmp)) > 0x00) {
                    /* If the alpha channel is set to 0x00, but there is color data
                     * on R-, G- and B-channel increase alpha to 0xFF, because
                     * they were modified by DrawText */
                    tmp->rgbReserved = 0xFF;
                }
                else {
                    /* Restore the alpha channel of the pixel. This is only required,
                     * if the color of the pixel is black, because the check
                     * above does not catch that color (=0x00000000) */
                    tmp->rgbReserved = alpha_channel[y * rect_width + x];
                }
            }
        }
    }

    /* Cleaning up */
    free(wtext_msg);
    free(alpha_channel);
    SelectObject(hdc_image, old_image);
    SelectObject(hdc_text, old_text);
    SelectObject(hdc_text, old_font);
    DeleteDC(hdc_text);
    DeleteDC(hdc_image);

    return hbitmap_text;
}

/*
 * Draws or updates the splash screen.
 *
 * If a text is passed, i.e. text_msg != NULL, a separate image with
 * text is drawn, which is then overlaid over the background image.
 */
static int
win32HandlePaint(HWND hWnd, SPLASHWINDOWSTATE *pState, char *text_msg)
{
    BLENDFUNCTION blend = {0};
    HDC hdc_screen, hdc_result;
    HBITMAP old_result, hbitmap_result = NULL;
    POINT pt_zero = {0};

    /* Blend bitmap with alpha channel for transparent images */
    blend.AlphaFormat = AC_SRC_ALPHA;
    blend.SourceConstantAlpha = 0xff;
    blend.BlendFlags = 0;
    blend.BlendOp = AC_SRC_OVER;

    /* Create necessary DCs for the window */
    hdc_screen = GetDC(NULL);
    hdc_result = CreateCompatibleDC(hdc_screen);

    if (text_msg != NULL) {
        hbitmap_result = win32HandleText(pState, hdc_screen, text_msg);
        old_result = (HBITMAP) SelectObject(hdc_result, hbitmap_result);

        /* Free text_msg, because the caller of this function might have called
         * this function again, because the caller is running in a different
         * thread. This function is responsible for freeing text_msg up to
         * this point.
         */
        free(text_msg);
    }
    else {
        /* Select the splash bitmap into the display DC */
        old_result = (HBITMAP) SelectObject(hdc_result, pState->splash_bitmap);
    }

    /* Update layered window */
    if (!UpdateLayeredWindow(hWnd,
                             hdc_screen,
                             NULL,
                             &pState->wnd_size,
                             hdc_result,
                             &pt_zero,
                             (COLORREF) 0,
                             &blend,
                             pState->wnd_blendmode)) {
        FATAL_WINERROR("UpdateLayeredWindow", "Cannot Update Window.\n");
        return -1;
    }

    /* Cleaning up */
    SelectObject(hdc_result, old_result);

    if (hbitmap_result != NULL) {
        DeleteObject(hbitmap_result);
    }
    DeleteDC(hdc_result);
    ReleaseDC(NULL, hdc_screen);
    return 0;
}

/* Callback function for messages from Windows to the splash screen window. */
LRESULT CALLBACK
win32WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    SPLASHWINDOWSTATE *pState;

    /*
     * The WM_PAINT message is not sent for a layered window
     * if per-pixel alpha blending is enabled.
     *
     * If a window was created with WS_EX_LAYERED, then there are two options:
     * - By calling SetLayeredWindowAttributes with a ColorKey WM_PAINT messages are sent.
     *   SetLayeredWindowAttributes supports only opaque, uniform transparency and
     *   chroma-keying blend effects. Per-pixel alpha is not supported.
     * - By using UpdateLayeredWindow all blending effects are supported. However,
     *   WM_PAINT messages are no longer sent, so rendering must be done manually.
     */
    switch (message) {
        case WM_CREATE:
            pState = ((CREATESTRUCT *) lParam)->lpCreateParams;
            SetWindowLongPtr(hWnd, GWLP_USERDATA, (LONG_PTR) pState);
            return win32HandlePaint(hWnd, pState, NULL);

        case _WM_SPLASH:
            pState = (SPLASHWINDOWSTATE *) GetWindowLongPtr(hWnd, GWLP_USERDATA);
            return win32HandlePaint(hWnd, pState, (char *) lParam);

        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;

        default:
            break;
    }
    return DefWindowProc(hWnd, message, wParam, lParam);
}

/* Register Window */
static ATOM
win32RegisterWindow()
{
    WNDCLASSEX wc;

    wc.cbSize = sizeof(WNDCLASSEX);
    wc.style = 0;
    wc.lpfnWndProc = win32WndProc;
    wc.cbClsExtra = 0;
    wc.cbWndExtra = 0;
    wc.hInstance = GetModuleHandle(NULL);
    wc.hIcon = NULL;
    wc.hIconSm = NULL;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = NULL;
    wc.lpszMenuName = NULL;
    wc.lpszClassName = _SPLASH_WINDOW_NAME;

    return RegisterClassEx(&wc);
}

/* Create Microsoft Windows Splash Screen */
static HWND
win32CreateWindow(SPLASHWINDOWSTATE *window_state)
{
    return CreateWindowEx(
        WS_EX_TOOLWINDOW | WS_EX_LAYERED,                            /* Optional window style */
        _SPLASH_WINDOW_NAME,                                         /* Window class */
        NULL,                                                        /* Window text */
        WS_POPUP,                                                    /* Windows style */
        window_state->wnd_origin.x, window_state->wnd_origin.y,      /* Position */
        window_state->wnd_size.cx, window_state->wnd_size.cy,        /* Size */
        NULL,                                                        /* Parent window */
        NULL,                                                        /* Menu */
        GetModuleHandle(NULL),                                       /* Instance handle */
        window_state);                                               /* Additional application data */
}

/* Calculate the centered position of a given size on the primary monitor. */
static POINT
win32WindowOrigin(SIZE bitmap_size)
{
    POINT ptOrigin, ptZero = {0};
    HMONITOR hPrimary;
    MONITORINFO monitor_info;
    RECT rcWork;

    /* Get the primary monitor's info */
    hPrimary = MonitorFromPoint(ptZero, MONITOR_DEFAULTTOPRIMARY);

    monitor_info.cbSize = sizeof(MONITORINFO);
    GetMonitorInfo(hPrimary, &monitor_info);

    rcWork = monitor_info.rcWork;
    ptOrigin.x = rcWork.left + (rcWork.right - rcWork.left - bitmap_size.cx) / 2;
    ptOrigin.y = rcWork.top + (rcWork.bottom - rcWork.top - bitmap_size.cy) / 2;

    return ptOrigin;
}

int CALLBACK
win32LoadFontProc(const LOGFONT *lpelfe, const TEXTMETRIC *lpntme,
                  DWORD FontType, LPARAM lParam)
{
    /* If this function gets executed at least once, the system
     * found a font matching the required */
    return 0;
}

/* Create handle for a font by its name.
 * If font_name is empty or the font is not available, the function will
 * use the stylized default font of the OS (in most cases 'Segeo UI') */
static HFONT
win32LoadFont(char *font_name, int font_size)
{
    HFONT hfont;
    HDC hdc_screen;
    int font_installed;
    LOGFONT font = {0};

    hdc_screen = GetDC(NULL);

    /* Formula to convert font point size to device font size */
    font_size = -MulDiv(font_size, GetDeviceCaps(hdc_screen, LOGPIXELSY), 72);

    /* Check if font is installed on this machine */
    pyi_win32_utils_from_utf8(font.lfFaceName, font_name, 32);

    font.lfCharSet = DEFAULT_CHARSET;
    font_installed = !EnumFontFamiliesEx(hdc_screen,
                                         &font,
                                         win32LoadFontProc,
                                         0, 0);

    /* If font_text is empty or the requested font is not available on this
     * system the default system font should be used. */
    if (!font_name[0] || !font_installed) {
        /* Get system (stylized) default font */
        SystemParametersInfo(SPI_GETICONTITLELOGFONT,
                             sizeof(LOGFONT),
                             &font, 0);
    }

    hfont = CreateFont(font_size,
                       0, 0, 0,
                       FW_NORMAL,
                       FALSE, FALSE, FALSE,
                       DEFAULT_CHARSET,
                       OUT_DEVICE_PRECIS | OUT_STROKE_PRECIS,
                       CLIP_DEFAULT_PRECIS,
                       CLEARTYPE_QUALITY,
                       DEFAULT_PITCH,
                       font.lfFaceName);

    if (hfont == NULL) {
        /* Don't know how this could happen, but to be sure use the stock
         * font object (which is always available) */
        hfont = (HFONT) GetStockObject(DEFAULT_GUI_FONT);
    }

    ReleaseDC(NULL, hdc_screen);
    return hfont;
}

/*
 * Launches the splash screen for WIN32
 *
 * This function is executed in a separate thread.
 */
static void
win32Launch(void *param)
{
    SPLASH *splash;
    SPLASHWINDOWSTATE *window_state;
    HWND splash_window;
    MSG msg;

    RECT _text_rect = {0};
    SIZE _window_size = {0};

    /* Translate param to SPLASH struct (void* parameter is
     * necessary to comply with _beginthread function) */
    splash = (SPLASH *) param;

    /**
     * Build window_state
     */

    /* Allocate memory for window runtime data */
    window_state = (SPLASHWINDOWSTATE *) malloc(sizeof(SPLASHWINDOWSTATE));

    /* Get the position of the splash screen */
    _window_size.cx = ntohl(splash->wnd_width);
    _window_size.cy = ntohl(splash->wnd_height);
    window_state->wnd_size = _window_size;
    window_state->wnd_origin = win32WindowOrigin(_window_size);

    /* Setup splash screen image (handle, blend mode) */
    window_state->splash_bitmap = win32LoadBitmapHandle(splash);
    window_state->wnd_blendmode = splash->img_bit_count == 32 ?
                                  ULW_ALPHA :
                                  ULW_OPAQUE;

    if (window_state->splash_bitmap == NULL) {
        return;
    }

    /* Setup font (handle, color, rect) */
    _text_rect.left = ntohl(splash->txt_rect.left);
    _text_rect.top = ntohl(splash->txt_rect.top);
    _text_rect.right = ntohl(splash->txt_rect.right);
    _text_rect.bottom = ntohl(splash->txt_rect.bottom);
    window_state->wnd_text_rect = _text_rect;
    window_state->wnd_text_color = ntohl(splash->txt_clr);
    window_state->wnd_font = win32LoadFont(splash->txt_fontname,
                                           ntohl(splash->txt_fontsize));

    /* Free splash, since it is not needed anymore */
    free(splash);
    splash = NULL;

    /**
     * Create Window
     */

    /* Register splash window */
    if (!win32RegisterWindow()) {
        FATALERROR("Failed To Register The Window Class.\n");
        return;
    }

    /* Create splash window */
    splash_window = win32CreateWindow(window_state);

    if (splash_window == NULL) {
        FATALERROR("Splash Window Creation Failed.\n");
        return;
    }
    VS("SPLASH: Successful registration of all Microsoft Windows Handles.\n");

    /* Show window and enter main loop */
    ShowWindow(splash_window, SW_SHOW);

    /* Main loop
     * This loop blocks this thread until the window of the splash
     * screen closes */
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    /* Cleaning up */
    DestroyWindow(splash_window);
    UnregisterClass(_SPLASH_WINDOW_NAME,
                    GetModuleHandle(NULL));
    DeleteObject(window_state->wnd_font);
    DeleteObject(window_state->splash_bitmap);
    free(window_state);
}

/*
 * Start an IPC server that waits for messages coming through the
 * pipe and forwards them accordingly.
 */
static void
win32IPCServer(void *param)
{
    HANDLE pipe_read_end;
    DWORD num_of_bytes;
    HWND splashWindow;

    /* Use a simple protocol to communicate through the pipe
     * ipc_message[0]   := event type
     * ipc_message[1:5] := custom event data length
     * ipc_message[>5]  := custom event data */
    IPC_MESSAGE_HEAD msg_buffer = {0};
    char *text_buffer = NULL;

    pipe_read_end = (HANDLE) param;

    /* Wait for another process to connect to the pipe.
     *
     * ConnectNamedPipe blocks this thread. This thread will not continue until
     * the Python interpreter is fully started and the pyi_splash module has
     * been executed.
     */
    if (ConnectNamedPipe(pipe_read_end, NULL) == 0) {
        FATAL_WINERROR("ConnectNamedPipe", "Failed to wait for connecting with pipe\n");
        _endthread();
    }

    num_of_bytes = 0;

    /* Loop that continuously reads data from the pipe, if any is present.
     * ReadFile blocks if no data can be read, so this needs to run in a separate thread */
    while (1) {
        /* Read the head of the message */
        ReadFile(pipe_read_end,
                 &msg_buffer,
                 sizeof(IPC_MESSAGE_HEAD),
                 &num_of_bytes,
                 NULL);

        /* Client disconnected */
        if (GetLastError() == ERROR_BROKEN_PIPE && num_of_bytes == 0) {
            break;
        }

        /* If the message carries more data, load it into text_buffer */
        if (msg_buffer.text_length != 0 && GetLastError() == ERROR_MORE_DATA) {
            /* Text with string/null terminator */
            text_buffer = (char *) calloc(1, msg_buffer.text_length + 1);

            ReadFile(pipe_read_end,
                     text_buffer,
                     msg_buffer.text_length,
                     &num_of_bytes,
                     NULL);
        }

        /* Search for the window again at every message, if the splash screen was closed without
         * informing this loop. */
        splashWindow = win32GetCurrentSplashWindow();

        if (splashWindow == NULL) {
            break;
        }

        /* Command "check tree" */
        if (msg_buffer.event_type == _IPC_MSG_FINISH) {
            /* The Window is closed outside the loop */
            break;
        }
        else if (msg_buffer.event_type == _IPC_MSG_UPDATE) {
            PostMessage(splashWindow, _WM_SPLASH, 0, (LPARAM) text_buffer);
            text_buffer = NULL;
        }
        else {
            VS("SPLASH: IPC Server received message of unknown type (%d)\n",
               msg_buffer.event_type);
        }
    }

    /* If the client disconnects from the server, the splash screen should be closed,
     * because the IPC server closes and does not receive any further commands */
    splashWindow = win32GetCurrentSplashWindow();

    if (splashWindow != NULL) {
        VS("SPLASH: Closing splash screen\n");
        PostMessage(splashWindow, WM_QUIT, 0, 0);
    }

    /* Cleaning up */
    if (DisconnectNamedPipe(pipe_read_end) == 0) {
        FATAL_WINERROR("DisconnectNamedPipe", "Failed to disconnect from pipe\n");
    }
    CloseHandle(pipe_read_end);
}

#endif  /* _WIN32 */

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
#if defined(_WIN32)
    /* For Windows it is required to run the UI and message loop in a separate thread */
    _beginthread(
        win32Launch,
        0,
        splash);

    return 0;
#else  /* if defined(_WIN32) */
    VS("SPLASH: This bootloader does not support splash screen\n");
    return -1;
#endif  /* if defined(_WIN32) */
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

#ifdef _WIN32
    HANDLE pipe_read;

    /* Create a unique pipe name. This name is passed to the python process
     * via the _PYIBoot_SPLASH environment variable so that the process
     * can connect to this pipe. This allows two different splash screens
     * from different applications (built with pyinstaller) to run side
     * by side without affecting each other. Windows limits pipe names
     * to 256 characters */
    _pipe_name = (char *) malloc(256 * sizeof(char));

    /* The pipe name is generated using the current PID, so the pipe is unique
     * for each PyInstaller program running in parallel. */
    sprintf_s(_pipe_name, 256, "\\\\.\\pipe\\pyi_splash_pipe_%d", getpid());

    /* Create a named pipe with a unique name so that only the python process can
     * connect to the pipe. Responses to messages are not supported, so the commands
     * must be checked for correctness in the IPC client. This, while being the
     * IPC server, receives the messages and sends it to the splash screen thread.
     * A named pipe is used to avoid rewriting pyi_utils_create_child. This also
     * separates the splash screen as a module from the key components of the bootloader. */
    pipe_read = CreateNamedPipe(pyi_win32_utils_from_utf8(NULL, _pipe_name, 0), /* lpName */
                                PIPE_ACCESS_INBOUND,                            /* dwOpenMode */
                                PIPE_TYPE_MESSAGE                               /* dwPipeMode */
                                | PIPE_READMODE_MESSAGE
                                | PIPE_WAIT,
                                1,                                              /* nMaxInstances*/
                                2048,                                           /* nOutBufferSize */
                                2048,                                           /* nInBufferSize */
                                INFINITE,                                       /* nDefaultTimeOut */
                                NULL);                                          /* lpSecurityAttributes */

    if (pipe_read == INVALID_HANDLE_VALUE) {
        FATAL_WINERROR("CreateNamedPipe",
                       "Failed to create inbound pipe instance.\n");
        return NULL;
    }
    VS("SPLASH: Successfully created inbound pipe instance %s\n", _pipe_name);

    /* In order to read asynchronously from the pipe and not block the UI thread,
     * as well as the bootloader thread, the IPC server must run in a separate one. */
    _beginthread(
        win32IPCServer,
        0,
        pipe_read);

    return _pipe_name;
#else  /* ifdef _WIN32 */
    VS("SPLASH: This bootloader does not support splash screen\n");
    return NULL;
#endif  /* _WIN32 */
}
