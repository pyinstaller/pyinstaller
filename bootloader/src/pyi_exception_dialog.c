/*
 * ****************************************************************************
 * Copyright (c) 2021, PyInstaller Development Team.
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
 * Implementation of unhandled exception dialog for windowed mode on Windows.
 */

#if defined(WINDOWED) && defined(_WIN32)

#include <stdio.h>
#include <windows.h>
#include <commctrl.h>

#include "pyi_global.h"
#include "pyi_win32_utils.h"


/*
 * Dialog template structure, described in
 * https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-dlgtemplate
 */

/* The template structure must be aligned on WORD boundaries */
#pragma pack(push, 4)

typedef struct
{
    /* DLGTEMPLATE */
    DWORD style;
    DWORD dwExtendedStyle;
    WORD  cdit;
    short x;
    short y;
    short cx;
    short cy;

    /*
     * As per above MSDN link, in a standard template for a dialog box,
     * the DLGTEMPLATE structure is always immediately followed by three
     * variable-length arrays that specify the menu, class, and title
     * for the dialog box.
     *
     * When the DS_SETFONT style is specified, these arrays are also
     * followed by a 16-bit value specifying point size and another
     * variable-length array specifying a typeface name.
     *
     * In our implementation, we use 64-character fields for strings
     * we want to pass and WORD fields for unused entries.
     */
    WORD menu;
    WORD windowClass;
    WCHAR wszTitle[64];

    WORD pointsize;
    WCHAR wszFont[64];
} DIALOG_TEMPLATE;

#pragma pack(pop)


/* The dialog context, which we use to pass data between callbacks */
typedef struct
{
    HINSTANCE hInstance;  /* Parent module instance */
    HWND hDialog;  /* Dialog handle */

    /* Input exception data to display */
    WCHAR *wszScriptName;
    WCHAR *wszExceptionMessage;
    WCHAR *wszTraceback;

    /* Formatted label message */
    WCHAR wszLabelMessage[PATH_MAX];

    /* UI elements / controls */
    HWND hStaticIcon;
    HWND hStaticLabel;
    HWND hTracebackView;
    HWND hCloseButton;

    /* Resources */
    HFONT hDialogFont;
    HICON hErrorIcon;

    /* Misc */
    WORD wMargin;
    WORD wButtonWidth;
    WORD wButtonHeight;
    WORD wIconWidth;
    WORD wIconHeight;
} DIALOG_CONTEXT;


/* Resize the dialog's contents to the new client area width and height. */
static void
_exception_dialog_resize(DIALOG_CONTEXT *dialog, WORD wAreaWidth, WORD wAreaHeight)
{
    WORD wLabelHeight;
    WORD wPosY, wPosX, wWidth, wHeight;
    HDC hDC;

    /* Estimate the required height of the text label. */
    hDC = GetDC(dialog->hStaticLabel);
    if (hDC) {
        HFONT hOldFont = NULL;
        RECT rectText;

        rectText.left = 0;
        rectText.top = 0;
        rectText.right = wAreaWidth - 3*dialog->wMargin - dialog->wIconWidth;
        rectText.bottom = 0;

        /* Estimate text rectangle */
        if (dialog->hDialogFont) {
            /* To obtain correct font metrics, we need to select the
             * font into device context */
            hOldFont = SelectObject(hDC, dialog->hDialogFont);
        }
        DrawTextW(hDC, dialog->wszLabelMessage, -1, &rectText, DT_LEFT | DT_CALCRECT | DT_NOCLIP | DT_WORDBREAK | DT_EDITCONTROL | DT_EXPANDTABS);
        /* Cleanup */
        if (dialog->hDialogFont) {
            SelectObject(hDC, hOldFont);  /* Restore old font, just in case */
        }
        ReleaseDC(dialog->hStaticLabel, hDC);
        /* Estimate label height */
        wLabelHeight = (WORD)(rectText.bottom - rectText.top);
    } else {
        /* Fall-back value, just in case */
        wLabelHeight = 20;
    }
    if (wLabelHeight < dialog->wIconHeight) {
        wLabelHeight = dialog->wIconHeight;
    }

    /*
     * Adjust controls' position and size
     */
    /* Icon */
    wPosX = dialog->wMargin;
    wPosY = dialog->wMargin;
    wWidth = dialog->wIconWidth;
    wHeight = dialog->wIconHeight;
    MoveWindow(dialog->hStaticIcon, wPosX, wPosY, wWidth, wHeight, TRUE);

    /* Label */
    wPosX = dialog->wMargin + dialog->wIconWidth + dialog->wMargin;
    wPosY = dialog->wMargin;
    wWidth = wAreaWidth - dialog->wMargin - wPosX;
    wHeight = wLabelHeight;
    MoveWindow(dialog->hStaticLabel, wPosX, wPosY, wWidth, wHeight, TRUE);

    /* Traceback view */
    wPosX = dialog->wMargin;
    wPosY += wLabelHeight + dialog->wMargin;
    wWidth = wAreaWidth - dialog->wMargin - wPosX;
    wHeight = wAreaHeight - wPosY - dialog->wMargin - dialog->wButtonHeight - dialog->wMargin;
    MoveWindow(dialog->hTracebackView, wPosX, wPosY, wWidth, wHeight, TRUE);

    /* Close button */
    wPosX = wAreaWidth - dialog->wMargin - dialog->wButtonWidth;
    wPosY = wAreaHeight - dialog->wMargin - dialog->wButtonHeight;
    wWidth = dialog->wButtonWidth;
    wHeight = dialog->wButtonHeight;
    MoveWindow(dialog->hCloseButton, wPosX, wPosY, wWidth, wHeight, TRUE);
}


/* Initialize the dialog. */
static void
_exception_dialog_initialze(DIALOG_CONTEXT *dialog)
{
    NONCLIENTMETRICSW metrics;
    LONG lUnits;
    RECT rect;

    /*
     * Initialize resources
     */
    /* Format the label message */
    swprintf(dialog->wszLabelMessage, PATH_MAX, L"Failed to execute script '%ls' due to unhandled exception: %ls", dialog->wszScriptName, dialog->wszExceptionMessage);

    /* Estimate button dimensions */
    lUnits = GetDialogBaseUnits();
    dialog->wButtonWidth = MulDiv(LOWORD(lUnits), 50, 4);
    dialog->wButtonHeight = MulDiv(HIWORD(lUnits), 14, 8);

    /* Set icon dimensions */
    dialog->wIconWidth = 32;
    dialog->wIconHeight = 32;

    /* Set margin in the layout */
    dialog->wMargin = 8;

    /* Query default dialog font*/
    ZeroMemory(&metrics, sizeof(metrics));
    metrics.cbSize = sizeof(metrics);
    if (SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, metrics.cbSize, &metrics, 0)) {
        dialog->hDialogFont = CreateFontIndirectW(&metrics.lfMessageFont);
    } else {
        dialog->hDialogFont = NULL;
    }

    /* Load the icon; LoadIconMetric() gives modern icon, but requires
     * Microsoft.Windows.Common-Controls version='6.0.0.0' dependency
     * in the manifest. */
    // dialog->hErrorIcon = LoadIconW(NULL, MAKEINTRESOURCEW(IDI_ERROR));
    LoadIconMetric(NULL, MAKEINTRESOURCEW(IDI_ERROR), LIM_LARGE, &dialog->hErrorIcon);

    /*
     * Create UI controls
     * NOTE: positions and dimensions of controls do not matter, as we
     * reposition and resize them using dynamic layout function.
     */
    /* Icon */
    dialog->hStaticIcon = CreateWindowExW(
        0,
        L"STATIC",
		NULL,
		WS_CHILD | WS_VISIBLE | SS_ICON,
		CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT,
		dialog->hDialog,
		NULL,
		dialog->hInstance,
		NULL
    );

    /* Basic information label */
    dialog->hStaticLabel = CreateWindowExW(
        0,
        L"STATIC",
		NULL,
		WS_CHILD | WS_VISIBLE | SS_LEFT,
		CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT,
		dialog->hDialog,
		NULL,
		dialog->hInstance,
		NULL
    );

    /* Create traceback view (text edit) */
    dialog->hTracebackView = CreateWindowExW(
        WS_EX_CLIENTEDGE,  /* border */
        L"EDIT",
		NULL,
		WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_HSCROLL |ES_LEFT |ES_MULTILINE | ES_AUTOHSCROLL | ES_READONLY,
		CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT,
		dialog->hDialog,
		NULL,
		dialog->hInstance,
		NULL
    );

    /* Close button */
    dialog->hCloseButton = CreateWindowExW(
        0,
        L"BUTTON",
		L"Close",
		WS_CHILD | WS_VISIBLE | BS_DEFPUSHBUTTON,
		CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT,
		dialog->hDialog,
		(HMENU)(UINT_PTR)IDOK,  /* assign control ID */
		dialog->hInstance,
		NULL
    );

    /* Set icon */
    SendMessageW(dialog->hDialog, WM_SETICON, ICON_SMALL, (LPARAM)dialog->hErrorIcon);
    SendMessageW(dialog->hDialog, WM_SETICON, ICON_BIG, (LPARAM)dialog->hErrorIcon);
    SendMessageW(dialog->hStaticIcon, STM_SETIMAGE, (WPARAM)IMAGE_ICON, (LPARAM)dialog->hErrorIcon);

    /* Set font to dialog and controls */
    if (dialog->hDialogFont) {
        SendMessageW(dialog->hDialog, WM_SETFONT, (WPARAM)dialog->hDialogFont, TRUE);
        SendMessageW(dialog->hStaticLabel, WM_SETFONT, (WPARAM)dialog->hDialogFont, TRUE);
        SendMessageW(dialog->hTracebackView, WM_SETFONT, (WPARAM)dialog->hDialogFont, TRUE);
        SendMessageW(dialog->hCloseButton, WM_SETFONT, (WPARAM)dialog->hDialogFont, TRUE);
    }

    /* Set text to controls */
    SendMessageW(dialog->hStaticLabel, WM_SETTEXT, 0, (LPARAM)dialog->wszLabelMessage);
    SendMessageW(dialog->hTracebackView, WM_SETTEXT, 0, (LPARAM)dialog->wszTraceback);

    /* Perform initial resize */
    if (GetClientRect(dialog->hDialog, &rect)) {
        _exception_dialog_resize(
            dialog,
            (WORD)(rect.right - rect.left),
            (WORD)(rect.bottom - rect.top)
        );
    }
}


/* Clean up dialog data */
static void
_exception_dialog_cleanup(DIALOG_CONTEXT *dialog)
{
    /* Clean-up exception data */
    free(dialog->wszScriptName);
    free(dialog->wszExceptionMessage);
    free(dialog->wszTraceback);

    /* Free font */
    if (dialog->hDialogFont) {
        DeleteObject(dialog->hDialogFont);
    }

    /* Free icon */
    if (dialog->hErrorIcon) {
        DestroyIcon(dialog->hErrorIcon);
    }
}


/* The DLGPROC callback procedure */
static INT_PTR CALLBACK
_exception_dialog_proc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    switch (uMsg) {
        case WM_INITDIALOG: {
            DIALOG_CONTEXT *dialog = (DIALOG_CONTEXT *)lParam;
            /* Store dialog handle in the context */
            dialog->hDialog = hwnd;
            /* Set pointer to context data as dialog's user data, so we
             * can retrieve it in other commands */
            SetWindowLongPtrW(hwnd, DWLP_USER, lParam);
            /* Initialize dialog */
           _exception_dialog_initialze(dialog);
           return TRUE;
        }
        case WM_COMMAND: {
            UINT wId = LOWORD(wParam);
            if (wId == IDOK || wId == IDCANCEL) {
                EndDialog(hwnd, wId);
            }
            return TRUE;
        }
        case WM_CLOSE: {
            EndDialog(hwnd, IDCANCEL);
            return TRUE;
        }
        case WM_SIZE: {
            DIALOG_CONTEXT *dialog = (DIALOG_CONTEXT *)GetWindowLongPtrW(hwnd, DWLP_USER);
            /* Resize dialog UI */
            _exception_dialog_resize(dialog, LOWORD(lParam), HIWORD(lParam));
            /* Redraw */
            InvalidateRect(hwnd, NULL, FALSE);
            break;
        }
    }

    return FALSE;
}


/* Create and display modal dialog with information about uncaught exception */
static int
_pyi_unhandled_exception_dialog_w(const wchar_t *script_name, const wchar_t *exception_message, const wchar_t *traceback)
{
    HINSTANCE hInstance;
    DIALOG_TEMPLATE template;
    DIALOG_CONTEXT dialog;
    int ret;

    hInstance = GetModuleHandleW(NULL);

    /* Prepare template for empty dialog */
    ZeroMemory(&template, sizeof(template));

    template.style = WS_POPUP | WS_VISIBLE | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME| DS_MODALFRAME | DS_3DLOOK | DS_CENTER;
    template.dwExtendedStyle = 0;
    template.cdit = 0;  /* No items in template; we'll create them manually */
    template.x = 0;
    template.y = 0;
    template.cx = 200;
    template.cy = 150;
    template.menu = 0;
    template.windowClass = 0;
    swprintf(template.wszTitle, sizeof(template.wszTitle)/sizeof(template.wszTitle[0]), L"Unhandled exception in script");

    /* Prepare dialog context */
    ZeroMemory(&dialog, sizeof(dialog));
    dialog.hInstance = hInstance;

    dialog.wszScriptName = wcsdup(script_name);
    dialog.wszExceptionMessage = wcsdup(exception_message);
    dialog.wszTraceback = wcsdup(traceback);

    /* Create and run the dialog */
    ret = (int)DialogBoxIndirectParamW(hInstance, (LPCDLGTEMPLATEW)&template, NULL, _exception_dialog_proc, (LPARAM)&dialog);

    /* Cleanup */
    _exception_dialog_cleanup(&dialog);

    return ret;
}

/* The actual entry point function */
int
pyi_unhandled_exception_dialog(const char *script_name, const char *exception_message, const char *traceback)
{
    wchar_t *script_name_w = NULL;
    wchar_t *exception_message_w = NULL;
    wchar_t *traceback_w = NULL;
    int ret;

    if (script_name) {
        script_name_w = pyi_win32_utils_from_utf8(NULL, script_name, 0);
    }
    if (exception_message) {
        exception_message_w = pyi_win32_utils_from_utf8(NULL, exception_message, 0);
    }
    if (traceback) {
        traceback_w = pyi_win32_utils_from_utf8(NULL, traceback, 0);
    }

    ret = _pyi_unhandled_exception_dialog_w(script_name_w, exception_message_w, traceback_w ? traceback_w : L"Failed to obtain/convert traceback!");

    free(script_name_w);
    free(exception_message_w);
    free(traceback_w);

    return ret;
}

#endif
