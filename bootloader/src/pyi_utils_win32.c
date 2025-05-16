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
 * Utility functions. This file contains implementations that are specific
 * to Windows.
 */

/* Having a header included outside of the ifdef block prevents the compilation
 * unit from becoming empty, which is disallowed by pedantic ISO C. */
#include "pyi_global.h"

#ifdef _WIN32

#include <windows.h>
#include <io.h> /* _get_osfhandle */
#include <process.h> /* _getpid */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sddl.h> /* ConvertStringSecurityDescriptorToSecurityDescriptorW */
#include <psapi.h> /* K32EnumProcessModules, GetModuleFileNameExW */

/* PyInstaller headers. */
#include "pyi_utils.h"
#include "pyi_path.h"
#include "pyi_main.h"


/**********************************************************************\
 *                  Environment variable management                   *
\**********************************************************************/
char *
pyi_getenv(const char *variable)
{
    wchar_t *variable_w;
    wchar_t value[PYI_PATH_MAX];
    wchar_t expanded_value[PYI_PATH_MAX];
    DWORD rc;

    /* Convert the variable name from UTF-8 to wide-char */
    variable_w = pyi_win32_utf8_to_wcs(variable, NULL, 0);

    /* Retrieve environment variable */
    rc = GetEnvironmentVariableW(variable_w, value, PYI_PATH_MAX);
    if (rc >= PYI_PATH_MAX) {
        return NULL; /* Insufficient buffer size */
    }
    if (rc == 0) {
        return NULL; /* Variable unavailable */
    }

    /* Expand environment variables within the environment variable's
     * value */
    rc = ExpandEnvironmentStringsW(value, expanded_value, PYI_PATH_MAX);
    if (rc >= PYI_PATH_MAX) {
        return NULL; /* Insufficient buffer size */
    }
    if (rc == 0) {
        return NULL; /* Error during expansion */
    }

    /* Convert to UTF-8 and return */
    return pyi_win32_wcs_to_utf8(expanded_value, NULL, 0);
}

int
pyi_setenv(const char *variable, const char *value)
{
    int rc;
    wchar_t *variable_w;
    wchar_t *value_w;

    /* Convert from UTF-8 to wide-char */
    variable_w = pyi_win32_utf8_to_wcs(variable, NULL, 0);
    value_w = pyi_win32_utf8_to_wcs(value, NULL, 0);

    /* `SetEnvironmentVariableW` updates only the value in the process
     * environment block, while _wputenv_s updates the value in the CRT
     * block AND calls `SetEnvironmentVariableW` to update the process
     * environment block.
     *
     * Therefore, in order for modification to be visible to other CRT
     * functions (for example, `_wtempnam`), we must use `_wputenv_s`. */
    rc = _wputenv_s(variable_w, value_w);

    free(variable_w);
    free(value_w);

    return rc;
}

int
pyi_unsetenv(const char *variable)
{
    int rc;
    wchar_t *variable_w;

    /* Convert from UTF-8 to wide-char */
    variable_w = pyi_win32_utf8_to_wcs(variable, NULL, 0);

    /* See the comment in `pyi_setenv`. As per MSDN, "You can remove a
     * variable from the environment by specifying an empty string (that
     * is, "") for value_string. */
    rc = _wputenv_s(variable_w, L"");

    free(variable_w);

    return rc;
}


/**********************************************************************\
 *         Temporary application top-level directory (onefile)        *
\**********************************************************************/
/* Resolve the temporary directory specified by user via runtime_tmpdir
 * option, and create corresponding directory tree. */
static wchar_t *
_pyi_create_runtime_tmpdir(const char *runtime_tmpdir)
{
    wchar_t *runtime_tmpdir_w;
    wchar_t runtime_tmpdir_expanded[PYI_PATH_MAX];
    wchar_t *runtime_tmpdir_abspath;
    wchar_t *subpath_cursor;
    wchar_t directory_tree_path[PYI_PATH_MAX];
    DWORD rc;

    /* Convert UTF-8 path to wide-char */
    runtime_tmpdir_w = pyi_win32_utf8_to_wcs(runtime_tmpdir, NULL, 0);
    if (!runtime_tmpdir_w) {
        PYI_ERROR_W(L"LOADER: failed to convert runtime-tmpdir to a wide string.\n");
        return NULL;
    }

    /* Expand environment variables like %LOCALAPPDATA% */
    rc = ExpandEnvironmentStringsW(runtime_tmpdir_w, runtime_tmpdir_expanded, PYI_PATH_MAX);
    free(runtime_tmpdir_w);
    if (!rc) {
        PYI_ERROR_W(L"LOADER: failed to expand environment variables in the runtime-tmpdir.\n");
        return NULL;
    }

    /* Check if runtime-tmpdir is just a disk drive root (e.g., "c:\").
     * If so, validate the drive's existence, and return the path as-is.
     * There is no path to resolve (and calling `_wfullpath()` would end
     * up returning current working directory on the current drive), and
     * there is no directory structure to create */
    if (pyi_win32_is_drive_root(runtime_tmpdir_expanded)) {
        int drive_type = 0;
        PYI_DEBUG_W(L"LOADER: expanded runtime-tmpdir is a drive root: %ls\n", runtime_tmpdir_expanded);

        /* Ensure the given volume name is valid, i.e., includes the
         * backslash as per Windows path naming conventions:
         * https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
         * The `pyi_win32_is_drive_root` check ensures that the path is
         * either two or three characters long, so the third character
         * is either the backslash or terminating NUL. */
        if (runtime_tmpdir_expanded[2] != L'\\') {
            PYI_DEBUG_W(L"LOADER: appending backslash to the given drive root %ls\n", runtime_tmpdir_expanded);
            wcscat(runtime_tmpdir_expanded, L"\\");
        }

        /* Now ensure that the drive actually exists - raise error on
         * DRIVE_UNKNOWN (0) and DRIVE_NO_ROOT_DIR (1) */
        drive_type = GetDriveTypeW(runtime_tmpdir_expanded);
        if (drive_type <= DRIVE_NO_ROOT_DIR) {
            PYI_ERROR_W(L"LOADER: runtime-tmpdir points to non-existent drive %ls (type: %d)!\n", runtime_tmpdir_expanded, drive_type);
            return NULL;
        }

        return _wcsdup(runtime_tmpdir_expanded);
    }

    /* Resolve absolute path */
    runtime_tmpdir_abspath = _wfullpath(NULL, runtime_tmpdir_expanded, PYI_PATH_MAX);
    if (!runtime_tmpdir_abspath) {
        PYI_ERROR_W(L"LOADER: failed to obtain the absolute path of the runtime-tmpdir.\n");
        return NULL;
    }

    PYI_DEBUG_W(L"LOADER: absolute runtime-tmpdir is %ls\n", runtime_tmpdir_abspath);

    /* Recursively create the directory structure
     *
     * NOTE: we call CreateDirectoryW without security descriptor for
     * this part of directory tree, as it might be shared by application
     * instances ran by different users. Only the last component (the
     * actual _MEIXXXXXX directory), created by the caller, uses security
     * descriptor to restrict access to current user.
     *
     * NOTE2: we ignore errors returned by CreateDirectoryW; if we
     * actually fail to create (a part of) directory tree here, we will
     * catch the error in the caller when trying to create the final
     * temporary directory component. */
    for(subpath_cursor = wcschr(runtime_tmpdir_abspath, L'\\'); subpath_cursor != NULL; subpath_cursor = wcschr(++subpath_cursor, L'\\')) {
        int subpath_length = (int)(subpath_cursor - runtime_tmpdir_abspath);

        _snwprintf(directory_tree_path, PYI_PATH_MAX, L"%.*s", subpath_length, runtime_tmpdir_abspath);
        PYI_DEBUG_W(L"LOADER: creating runtime-tmpdir path component: %ls\n", directory_tree_path);
        CreateDirectoryW(directory_tree_path, NULL);
    }

    /* Run once more on full path, to handle cases when path did not end
     * with separator. Here, we also explicitly check that the call
     * succeeded or failed with ERROR_ALREADY_EXISTS, to properly report
     * errors in creation of temporary directory tree. */
    PYI_DEBUG_W(L"LOADER: creating runtime-tmpdir path: %ls\n", runtime_tmpdir_abspath);
    if (CreateDirectoryW(runtime_tmpdir_abspath, NULL) == 0) {
        if (GetLastError() != ERROR_ALREADY_EXISTS) {
            PYI_WINERROR_W(L"CreateDirectory", L"LOADER: failed to create runtime-tmpdir path %ls!\n", runtime_tmpdir_abspath);
            free(runtime_tmpdir_abspath);
            return NULL;
        }
    }

    return runtime_tmpdir_abspath;
}

int
pyi_create_temporary_application_directory(struct PYI_CONTEXT *pyi_ctx)
{
    char *original_tmp_value = NULL;
    wchar_t prefix[16];
    wchar_t tempdir_path[PYI_PATH_MAX];
    int ret = 0;
    int i;

    /* If user specified the temporary directory via runtime_tmpdir
     * option, resolve it, create it, and store the path to TMP
     * environment variable to have`GetTempPathW` use it. */
    if (pyi_ctx->runtime_tmpdir != NULL) {
        wchar_t *runtime_tmpdir_w;
        DWORD rc;

        /* Retrieve original value of TMP environment variable, so we
         * can restore it at the very end of this function. */
        original_tmp_value = pyi_getenv("TMP");

        /* Resolve and create directory specified via the runtime_tmpdir
         * option. */
        runtime_tmpdir_w = _pyi_create_runtime_tmpdir(pyi_ctx->runtime_tmpdir);
        if (runtime_tmpdir_w == NULL) {
            free(original_tmp_value);
            return -1;
        }

        /* Store the path in the TMP environment variable. */
        rc = _wputenv_s(L"TMP", runtime_tmpdir_w);
        free(runtime_tmpdir_w);
        if (rc) {
            PYI_ERROR_W(L"LOADER: failed to set the TMP environment variable.\n");
            free(original_tmp_value);
            return -1;
        }

        PYI_DEBUG_W(L"LOADER: successfully resolved the specified runtime-tmpdir\n");
    }

    /* Retrieve temporary directory */
    GetTempPathW(PYI_PATH_MAX, tempdir_path);
    PYI_DEBUG_W(L"LOADER: attempting to create temporary application directory under %ls\n", tempdir_path);

    /* Create _MEI + PID prefix */
    swprintf(prefix, 16, L"_MEI%d", _getpid());

    /* Windows does not have a race-free function to create a temporary
     * directory. Thus, we rely on _tempnam, and simply try several times
     * to avoid stupid race conditions. */
    for (i = 0; i < 5; i++) {
        wchar_t *application_home_dir_w = _wtempnam(tempdir_path, prefix);

        /* Try creating the directory. Use `CreateDirectoryW` with security
         * descriptor to limit access to current user. The functon returns
         * 0 on failure. */
        if (CreateDirectoryW(application_home_dir_w, pyi_ctx->security_attr) == 0) {
            free(application_home_dir_w);
            ret = -1; /* In case we reached max. retries */
        } else {
            /* Convert path to UTF-8 and store it in main context structure */
            if (pyi_win32_wcs_to_utf8(application_home_dir_w, pyi_ctx->application_home_dir, PYI_PATH_MAX) == NULL) {
                PYI_ERROR_W(L"LOADER: length of teporary directory path exceeds maximum path length!\n");
                ret = -1;
            } else {
                ret = 0; /* Re-set to zero in case this is not first iteration. */
            }
            free(application_home_dir_w);
            break;
        }
    }

    /* If we modified TMP environment variable due to runtime_tmpdir
     * option, restore the environment variable to its original state. */
    if (pyi_ctx->runtime_tmpdir != NULL) {
        if (original_tmp_value!= NULL) {
            pyi_setenv("TMP", original_tmp_value);
            free(original_tmp_value);
        } else {
            pyi_unsetenv("TMP");
        }
    }

    return ret;
}


/**********************************************************************\
 *                  Recursive removal of a directory                  *
\**********************************************************************/
/* The actual implementation with wide-char path */
static int
_pyi_recursive_rmdir(const wchar_t *dir_path)
{
    int dir_path_length;
    int buffer_size;
    wchar_t entry_path[PYI_PATH_MAX];
    HANDLE handle;
    WIN32_FIND_DATAW entry_info;

    /* Copy the directory path, and append separator and a wildcard for
     * the `FindFirstFileW()` call. Store the length of the directory
     * path plus the separator; this allows us to re-use the same buffer
     * for constructing entries' full paths, by overwriting only the
     * part of the string that follows the path separator that we added. */
    dir_path_length = _snwprintf(entry_path, PYI_PATH_MAX, L"%s\\*", dir_path);
    if (dir_path_length >= PYI_PATH_MAX) {
        return -1;
    }
    dir_path_length--; /* Ignore the wildcard at the end */
    buffer_size = PYI_PATH_MAX - dir_path_length; /* Remaining buffer size */

    /* Start the search by looking for first entry */
    handle = FindFirstFileW(entry_path, &entry_info);
    if (handle == INVALID_HANDLE_VALUE) {
        return -1;
    }

    do {
        /* Skip . and .. */
        if (wcscmp(entry_info.cFileName, L".") == 0 || wcscmp(entry_info.cFileName, L"..") == 0) {
            continue;
        }

        /* Construct the full path, by overwriting the part of string
         * that starts after path directory and separator. */
        if (_snwprintf(entry_path + dir_path_length, buffer_size, L"%s", entry_info.cFileName) >= buffer_size) {
            continue;
        }

        /* Deteremine the type of entry, and remove it. On errors, emit
         * debug messages to simplify debugging, and keep going on. We
         * want to remove everything we can; if we fail to remove an
         * entry here, we will also fail to remove the top-level
         * directory, and will return error there and then.
         * NOTE: do NOT emit warning or error messages here, as those
         * use dialogs in windowed/noconsole mode, and we don't want to
         * spam user with those! */
        if (entry_info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            /* Avoid recursing into symlinked directories */
            unsigned char is_symlink = 0;

            if (entry_info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) {
                if (entry_info.dwReserved0 == IO_REPARSE_TAG_SYMLINK) {
                    is_symlink = 1;
                }
            }

            if (is_symlink) {
                /* Remove only the symlink itself; return value is 1 on
                 * success, 0 on failure. */
                if (RemoveDirectoryW(entry_path) == 0) {
                    PYI_DEBUG_W(L"LOADER: failed to remove directory symbolic link: %ls\n", entry_path);
                }
            } else {
                /* Recurse into directory; return value is 0 on success,
                 * -1 on failure. */
                if (_pyi_recursive_rmdir(entry_path) < 0) {
                    PYI_DEBUG_W(L"LOADER: failed to remove directory: %ls\n", entry_path);
                }
            }
        } else {
            /* Delete file (or symlink to a file); return value is 1 on
             * success, 0 on failure. */
            if (DeleteFileW(entry_path) == 0) {
                PYI_DEBUG_W(L"LOADER: failed to remove file: %ls\n", entry_path);
            }
        }
    } while (FindNextFileW(handle, &entry_info) != 0);

    FindClose(handle);

    /* Finally, remove the directory */
    return RemoveDirectoryW(dir_path) != 1 ? -1 : 0; /* false/true-> -1/0 */
}


/* For now, the caller is supplying narrow-char path in  UTF-8 encoding. */
int
pyi_recursive_rmdir(const char *dir_path)
{
    wchar_t dir_path_w[PYI_PATH_MAX];
    pyi_win32_utf8_to_wcs(dir_path, dir_path_w, PYI_PATH_MAX);
    return _pyi_recursive_rmdir(dir_path_w);
}


/**********************************************************************\
 *                  Child process spawning (onefile)                  *
\**********************************************************************/
static BOOL WINAPI
_pyi_win32_console_ctrl(DWORD dwCtrlType)
{
    /* Due to different handling of PYI_DEBUG() macro in MSVC and mingw
     * gcc, the former requires the name variable below to be available
     * even in non-debug builds (where PYI_DEBUG() is no-op), while the
     * latter complains about the unused variable. So put everything
     * under ifdef guard to appease both. */
#if defined(LAUNCH_DEBUG)
    /* https://docs.microsoft.com/en-us/windows/console/handlerroutine */
    static const wchar_t *name_map[] = {
        L"CTRL_C_EVENT", /* 0 */
        L"CTRL_BREAK_EVENT", /* 1 */
        L"CTRL_CLOSE_EVENT", /* 2 */
        NULL,
        NULL,
        L"CTRL_LOGOFF_EVENT", /* 5 */
        L"CTRL_SHUTDOWN_EVENT" /* 6 */
    };
    const wchar_t *name = (dwCtrlType >= 0 && dwCtrlType <= 6) ? name_map[dwCtrlType] : NULL;

    /* NOTE: in case of CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, or
     * CTRL_SHUTDOWN_EVENT, the following message may not be printed to
     * console anymore. As per MSDN, the internal console cleanup routine
     * might have already been executed, preventing console functions
     * from working reliably. See Remarks section at:
     * https://docs.microsoft.com/en-us/windows/console/setconsolectrlhandler */
    PYI_DEBUG_W(L"LOADER: received console control signal %d (%ls)!\n", dwCtrlType, name ? name : L"unknown");
#endif /* defined(LAUNCH_DEBUG) */

    /* Handle Ctrl+C and Ctrl+Break signals immediately. By returning TRUE,
     * their default handlers (which would call ExitProcess()) are not
     * called, so we are effectively suppressing the signal here, while
     * letting the child process (who also received it) handle it as they
     * see it fit. */
    if (dwCtrlType == CTRL_C_EVENT || dwCtrlType == CTRL_BREAK_EVENT) {
        return TRUE;
    }

    /* Delay the inevitable for as long as we can. The same signal should
     * also be received by the child process (as it is in the same process
     * group as the parent), which will terminate (after optionally
     * processing the signal, if python code installed its own handler).
     * Therefore, we just wait here "forever" (compared to OS-imposed
     * timeout for signal handling) to buy time for the child process to
     * terminate and for the main thread of this (parent) process to
     * perform the cleanup (sidenote: this handler is executed in a
     * separate thread). So this thread is terminated either when the
     * main thread of the process finishes and the program exits
     * (gracefully), or when the time runs out and the OS kills everything (see
     * https://docs.microsoft.com/en-us/windows/console/handlerroutine#timeouts). */

    /* ... and then came the new shiny Windows Terminal and replaced
     * conhost.exe. In Windows terminal, the child process does not
     * seem to receive the event (until after the parent is terminated).
     * So we set a flag here that lets the main thread know that it
     * should terminate the child after a very short grace period. */
    global_pyi_ctx->console_shutdown = 1;

    Sleep(20000);
    return TRUE;
}

static HANDLE
_pyi_get_stream_handle(FILE *stream)
{
    HANDLE handle = (void *)_get_osfhandle(fileno(stream));
    /* When stdin, stdout, and stderr are not associated with a stream
     * (e.g., Windows application without console), _fileno() returns
     * special value -2. Therefore, call to _get_osfhandle() returns
     * INVALID_HANDLE_VALUE. If we caled _get_osfhandle() with 0, 1, or 2
     * instead of the result of _fileno(), _get_osfhandle() would also
     * return -2 when the file descriptor is not associated with the
     * stream. But because we take the _fileno() route, we need to handle
     * only INVALID_HANDLE_VALUE (= -1).
     * See: https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/get-osfhandle */
    if (handle == INVALID_HANDLE_VALUE) {
        return NULL;
    }
    return handle;
}

static
LRESULT CALLBACK _hidden_window_wndproc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    struct PYI_CONTEXT *pyi_ctx;
    switch (uMsg)
    {
        case WM_CREATE: {
            CREATESTRUCTW *create_struct = (CREATESTRUCTW *)lParam;
            pyi_ctx = (struct PYI_CONTEXT *)create_struct->lpCreateParams;
            SetWindowLongPtr(hwnd, GWLP_USERDATA, (LONG_PTR)pyi_ctx);
            return TRUE;
        }
        case WM_QUERYENDSESSION: {
            /* https://learn.microsoft.com/en-us/windows/win32/shutdown/wm-queryendsession */
            pyi_ctx = (struct PYI_CONTEXT *)GetWindowLongPtr(hwnd, GWLP_USERDATA);
            PYI_DEBUG_W(L"LOADER: hidden window received WM_QUERYENDSESSION with logoff-option %X\n", lParam);
            /* As per MSDN:
             * If your application may need more than 5 seconds to complete
             * its shutdown processing in response to WM_ENDSESSION, it
             * should call ShutdownBlockReasonCreate() in its
             * WM_QUERYENDSESSION handler, and promptly respond TRUE to
             * WM_QUERYENDSESSION so as not to block shutdown. It should
             * then perform all shutdown processing in its WM_ENDSESSION handler.
             *
             * https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms700677(v=vs.85)
             */
            if (!ShutdownBlockReasonCreate(hwnd, L"Needs to remove its temporary files.")) {
                PYI_DEBUG_W(L"LOADER: failed to register shutdown block reason (%d)!\n", GetLastError());
            }
            /* Set pyi_ctx->session_shutdown to let the rest of the code
             * know that we received WM_QUERYENDSESSION and that we
             * expect to receive and handle WM_ENDSESSION. */
            pyi_ctx->session_shutdown = 1;
            return TRUE;
        }
        case WM_ENDSESSION: {
            /* https://learn.microsoft.com/en-us/windows/win32/shutdown/wm-endsession */
            const int grace_period = 1000; /* milliseconds */

            pyi_ctx = (struct PYI_CONTEXT *)GetWindowLongPtr(hwnd, GWLP_USERDATA);
            PYI_DEBUG_W(L"LOADER: hidden window received WM_ENDSESSION with logoff-option %X and end-session option %X\n", lParam, wParam);

            if (!wParam) {
                PYI_DEBUG_W(L"LOADER: session shutdown has been canceled!\n");
                pyi_ctx->session_shutdown = 0; /* Clear the session shutdown flag */
                return 0; /* Message has been processed */
            }

            /* We need to perform cleanup here, before we exit this message
             * handler; at that point, Windows is free to terminate the
             * process (and will do so). */
            PYI_DEBUG_W(L"LOADER: session shutdown has been confirmed!\n");

            /* If child process is not already dead at this point, give
             * it a grace period to shut down on its own (or be terminated
             * by the OS for not processing WM_QUERYENDSESSION that it
             * also received), before terminating it ourselves. */
            PYI_DEBUG_W(L"LOADER: handling session shutdown - giving the child %d ms to exit...\n", grace_period);
            if (WaitForSingleObject(pyi_ctx->child_process.hProcess, grace_period) != WAIT_OBJECT_0) {
                PYI_DEBUG_W(L"LOADER: terminating the child process...\n");
                if (!TerminateProcess(pyi_ctx->child_process.hProcess, -1)) {
                    PYI_DEBUG_W(L"LOADER: TerminateProcess call failed (%d)\n", GetLastError());
                }

                /* If things don't play out as expected here, there is
                 * not really much we can do anyway, so do an infinite wait. */
                if (WaitForSingleObject(pyi_ctx->child_process.hProcess, INFINITE) == WAIT_OBJECT_0) {
                    PYI_DEBUG_W(L"LOADER: child process terminated!\n");
                } else {
                    PYI_DEBUG_W(L"LOADER: child process not terminated!\n");
                }
            } else {
                PYI_DEBUG_W(L"LOADER: child process has finished.\n");
            }
            /* The child process is presumed dead at this point. */

            /* Perform cleanup */
            PYI_DEBUG("LOADER: performing cleanup...\n");
            pyi_main_onefile_parent_cleanup(pyi_ctx);

            /* We can now die without regrets... */
            PYI_DEBUG("LOADER: end of WM_ENDSESSION handler reached!\n");
            return 0; /* Message has been processed */
        }
        default: {
            return DefWindowProc(hwnd, uMsg, wParam, lParam);
        }
    }
}

int
pyi_utils_create_child(struct PYI_CONTEXT *pyi_ctx)
{
    SECURITY_ATTRIBUTES security_attributes;
    STARTUPINFOW startup_info;
    wchar_t executable_filename_w[PYI_PATH_MAX];
    bool succeeded;
    DWORD child_exitcode;
    WNDCLASSW hidden_window_class;
    MSG msg;

    /* TODO is there a replacement for this conversion or just use wchar_t everywhere? */
    /* Convert file name to wchar_t from utf8. */
    pyi_win32_utf8_to_wcs(pyi_ctx->executable_filename, executable_filename_w, PYI_PATH_MAX);

    /* Set up console ctrl handler; the call returns non-zero on success */
    if (SetConsoleCtrlHandler(_pyi_win32_console_ctrl, TRUE) == 0) {
        PYI_DEBUG_W(L"LOADER: failed to install console ctrl handler!\n");
    }

    PYI_DEBUG_W(L"LOADER: setting up child process...\n");

    security_attributes.nLength = sizeof(security_attributes);
    security_attributes.lpSecurityDescriptor = NULL;
    security_attributes.bInheritHandle = TRUE;

    GetStartupInfoW(&startup_info);
    startup_info.lpReserved = NULL;
    startup_info.lpDesktop = NULL;
    startup_info.lpTitle = NULL;
    startup_info.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    startup_info.wShowWindow = SW_NORMAL;
    startup_info.hStdInput = _pyi_get_stream_handle(stdin);
    startup_info.hStdOutput = _pyi_get_stream_handle(stdout);
    startup_info.hStdError = _pyi_get_stream_handle(stderr);

    succeeded = CreateProcessW(
        executable_filename_w, /* lpApplicationName */
        GetCommandLineW(), /* lpCommandLine */
        &security_attributes, /* lpProcessAttributes */
        NULL, /* lpThreadAttributes */
        TRUE, /* bInheritHandles */
        0, /* dwCreationFlags */
        NULL, /* lpEnvironment */
        NULL, /* lpCurrentDirectory */
        &startup_info, /* lpStartupInfo */
        &pyi_ctx->child_process /* lpProcessInformation */
    );
    if (!succeeded) {
        PYI_WINERROR_W(L"CreateProcessW", L"Failed to create child process!\n");
        return -1;
    }
    PYI_DEBUG_W(L"LOADER: child process started!\n");

    /* Create a hidden window to capture WM_QUERYENDSESSION/WM_ENDSESSION
     * messages when user tries to end their Windows session (i.e., logs
     * off or initiates system shutdown or restart). */
    PYI_DEBUG_W(L"LOADER: creating hidden window to capture system shutdown events...\n");

    ZeroMemory(&hidden_window_class, sizeof(hidden_window_class));

    hidden_window_class.lpszClassName = L"PyInstallerOnefileHiddenWindow";
    hidden_window_class.lpfnWndProc = _hidden_window_wndproc;

    if (!RegisterClassW(&hidden_window_class)) {
        PYI_DEBUG_W(L"LOADER: failed to register hidden window class (%d)!\n", GetLastError());
    }

    pyi_ctx->hidden_window = CreateWindowExW(
        0, /* dwExStyle */
        hidden_window_class.lpszClassName, /* lpClassName */
        TEXT("PyInstaller Onefile Hidden Window"), /* lpWindowName */
        0, /* dwStyle */
        CW_USEDEFAULT, /* X */
        CW_USEDEFAULT, /* Y */
        CW_USEDEFAULT, /* nWidth */
        CW_USEDEFAULT, /* nHeight */
        NULL, /* hWndParent */
        NULL, /* hMenu */
        NULL, /* hInstance */
        pyi_ctx /* lpParam */
    );

    if (!pyi_ctx->hidden_window) {
        PYI_DEBUG_W(L"LOADER: failed to create hidden window (%d)!\n", GetLastError());
    } else {
        ShowWindow(pyi_ctx->hidden_window, SW_HIDE);
        PYI_DEBUG_W(L"LOADER: hidden window created!\n");
    }

    /* Wait for child process to exit, while also processing messages on
     * the hidden window and checking flags set from console handler. */
    PYI_DEBUG_W(L"LOADER: entering the waiting loop...\n");
    while (1) {
        DWORD ret;

        /* Poll the process status with 10 Hz frequency */
        ret = WaitForSingleObject(pyi_ctx->child_process.hProcess, 100);
        if (ret == WAIT_OBJECT_0) {
            PYI_DEBUG_W(L"LOADER: child process has finished - exiting the wait loop!\n");
            break; /* Child process has finished, for one reason or another. */
        }

        if (ret == WAIT_FAILED) {
            PYI_DEBUG_W(L"LOADER: WaitForSingleObject() failed with error code %d!\n", GetLastError());
        }

        /* If we received CTRL_CLOSE_EVENT, CTRL_SHUTDOWN_EVENT,
         * or CTRL_LOGOFF_EVENT from the installed console handler,
         * exit the loop and enter cleanup code. */
        if (pyi_ctx->console_shutdown) {
            PYI_DEBUG_W(L"LOADER: received console shutdown event - exiting the wait loop!\n");
            break;
        }

        /* Message pump for the hidden window. Use the non-blocking
         * PeekMessage, because wait/delay is already performed by the
         * WaitForSingleObject at the start of the loop. */
        while (PeekMessageW(&msg, pyi_ctx->hidden_window, 0, 0, PM_REMOVE) > 0) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }
    PYI_DEBUG_W(L"LOADER: made it out of the waiting loop!\n");

    /* If we received CTRL_CLOSE_EVENT, CTRL_SHUTDOWN_EVENT, or
     * CTRL_LOGOFF_EVENT from the installed console handler, give the
     * child process a short grace period to exit on its own (or be
     * terminated by the same event), before terminating it ourselves.
     * This seems to be required with the new Windows Terminal, where
     * (in contrast to old conhost.exe), the child process does not seem
     * to receive the event until after the OS terminates the parent. */
    if (pyi_ctx->console_shutdown) {
        const int grace_period = 500; /* milliseconds */
        PYI_DEBUG_W(L"LOADER: handling console shutdown - giving the child %d ms to exit...\n", grace_period);
        if (WaitForSingleObject(pyi_ctx->child_process.hProcess, grace_period) != WAIT_OBJECT_0) {
            PYI_DEBUG_W(L"LOADER: terminating the child process...\n");
            if (!TerminateProcess(pyi_ctx->child_process.hProcess, -1)) {
                PYI_DEBUG_W(L"LOADER: TerminateProcess call failed (%d)\n", GetLastError());
            }

            /* If things don't play out as expected here, there is
             * not really much we can do anyway, so do an infinite wait. */
            if (WaitForSingleObject(pyi_ctx->child_process.hProcess, INFINITE) == WAIT_OBJECT_0) {
                PYI_DEBUG_W(L"LOADER: child process terminated!\n");
            } else {
                PYI_DEBUG_W(L"LOADER: child process not terminated!\n");
            }
        } else {
            PYI_DEBUG_W(L"LOADER: child process has finished.\n");
        }
        /* The child process is presumed dead at this point */
    } else {
        /* The child process might have exited (or was terminated) due
         * to imminent shutdown event signalled by the WM_QUERYENDSESSION
         * message. This might happen before we had the chance to receive
         * and process WM_QUERYENDSESSION message in our main waiting loop.
         * So wait for a short time, on the off-chance that we receive
         * WM_QUERYENDSESSION; properly receiving and processing this
         * message ensures that OS gives us enough time to perform cleanup. */
        if (!pyi_ctx->session_shutdown) {
            LARGE_INTEGER start_time;
            LARGE_INTEGER frequency;
            LARGE_INTEGER current_time;
            LARGE_INTEGER elapsed_time;

            const int timeout = 250; /* milliseconds */
            const int short_timeout = 50; /* milliseconds */

            PYI_DEBUG_W(L"LOADER: waiting %d ms in case we receive WM_QUERYENDSESSION...\n", timeout);

            QueryPerformanceFrequency(&frequency); /* ticks per second */
            QueryPerformanceCounter(&start_time);

            /* This loop should exit after the hard-coded timeout, or
             * after we process WM_QUERYENDSESSION. If we also happen
             * to process WM_ENDSESSION here (with confirmed shutdown),
             * the WM_ENDSESSION handler will perform cleanup and let
             * the OS terminate this process, so we might actually not
             * make it past this loop. */
            while (1) {
                /* Perform short wait and check the message queue */
                MsgWaitForMultipleObjects(0, NULL, FALSE, short_timeout, QS_ALLINPUT);
                while (PeekMessageW(&msg, pyi_ctx->hidden_window, 0, 0, PM_REMOVE) > 0) {
                    TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }

                if (pyi_ctx->session_shutdown) {
                    PYI_DEBUG_W(L"LOADER: done waiting for WM_QUERYENDSESSION - message received!\n");
                    break;
                }

                QueryPerformanceCounter(&current_time);
                elapsed_time.QuadPart = current_time.QuadPart - start_time.QuadPart; /* ticks */
                elapsed_time.QuadPart *= 1000;
                elapsed_time.QuadPart /= frequency.QuadPart;

                PYI_DEBUG_W(L"LOADER: waited %lld ms / %d ms...\n", elapsed_time.QuadPart, timeout);
                if (elapsed_time.QuadPart >= timeout) {
                    PYI_DEBUG_W(L"LOADER: done waiting for WM_QUERYENDSESSION - timed-out!\n");
                    break;
                }
            }
        }

        /* If we received WM_QUERYENDSESSION, keep looping until we
         * also receive WM_ENDSESSION, which will either cancel or confirm
         * the shutdown. If the former, pyi_ctx->session_shutdow will
         * be cleared and we will proceed with the regular cleanup
         * codepath. If shutdown is confirmed, the WM_ENDSESSION handler
         * will peform cleanup and let the OS terminate this process, so
         * we might actually not make it past this loop. */
        if (pyi_ctx->session_shutdown) {
            PYI_DEBUG_W(L"LOADER: received session shutdown signal via WM_QUERYENDSESSION; waiting for WM_ENDSESSION...\n");
            while (pyi_ctx->session_shutdown) {
                /* We can use blocking GetMessageW here, because there
                 * are no other tasks to perform. */
                if (GetMessageW(&msg, pyi_ctx->hidden_window, 0, 0) > 0) {
                    TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
            }
            /* This point should not be reached, unless WM_ENDSESSION
             * message canceled the shutdown. */
        }
    }

    PYI_DEBUG_W(L"LOADER: retrieving process exit code and performing cleanup...\n");

    /* Clean up the hidden window */
    if (pyi_ctx->hidden_window) {
        DestroyWindow(pyi_ctx->hidden_window);
        pyi_ctx->hidden_window = NULL;
    }

    /* Retrieve the child exit code, and clean up child handles. */
    GetExitCodeProcess(pyi_ctx->child_process.hProcess, &child_exitcode);

    CloseHandle(pyi_ctx->child_process.hProcess);
    CloseHandle(pyi_ctx->child_process.hThread);

    return child_exitcode;
}


/**********************************************************************\
 *             Security descriptor for temporary directory            *
\**********************************************************************/
/* Retrieve the SID for the specified token information class from the current process.
 *
 * At the moment, TokenUser and TokenAppContainerSid are supported.
 *
 * Used in a compatibility work-around for wine, which at the time of writing
 * (version 5.0.2) does not properly support SID S-1-3-4 (directory owner),
 * and therefore user's actual SID must be used instead.
 *
 * Returns a copy of SID string on success, NULL on failure (or if the SID is unavailable
 * or zero-length). The returned string must be freed using LocalFree().
 */
static wchar_t *
_pyi_win32_get_sid(TOKEN_INFORMATION_CLASS token_information_class)
{
    HANDLE process_token = INVALID_HANDLE_VALUE;
    DWORD token_info_size = 0;
    void *token_info = NULL;
    wchar_t *sid = NULL;

    /* Get access token for the calling process */
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &process_token)) {
        goto cleanup;
    }

    /* Query buffer size and allocate buffer */
    if (!GetTokenInformation(process_token, token_information_class, NULL, 0, &token_info_size)) {
        if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
            goto cleanup;
        }
    }
    if (token_info_size == 0) {
        /* As per MSDN, in the Microsoft implementation, if number or size is zero, calloc
         * returns a pointer to an allocated block of non-zero size. An attempt to read or
         * write through the returned pointer leads to undefined behavior. */
        goto cleanup;
    }
    token_info = calloc(1, token_info_size);
    if (!token_info) {
        goto cleanup;
    }

    /* Get token information */
    if (!GetTokenInformation(process_token, token_information_class, token_info, token_info_size, &token_info_size)) {
        goto cleanup;
    }

    /* Convert SID to string */
    switch (token_information_class)
    {
        case TokenUser: {
            PTOKEN_USER user_info = (PTOKEN_USER)token_info;
            ConvertSidToStringSidW(user_info->User.Sid, &sid);
            break;
        }
        case TokenAppContainerSid: {
            PTOKEN_APPCONTAINER_INFORMATION app_container_info = (PTOKEN_APPCONTAINER_INFORMATION)token_info;
            ConvertSidToStringSidW(app_container_info->TokenAppContainer, &sid);
            break;
        }
        default: {
            /* Unsupoorted token information class */
            break;
        }
    }

    /* Cleanup */
cleanup:
    free(token_info);
    if (process_token != INVALID_HANDLE_VALUE) {
        CloseHandle(process_token);
    }

    return sid;
}

/* Initialize security descriptor applied to application's temporary directory and its
 * sub-directories.
 */
SECURITY_ATTRIBUTES *
pyi_win32_initialize_security_descriptor()
{
    SECURITY_ATTRIBUTES *security_attr;
    LPVOID lpSecurityDescriptor;
    wchar_t *user_sid;
    wchar_t *app_container_sid;
    wchar_t security_descriptor_str[PYI_PATH_MAX];
    int ret;

    /* Resolve user's SID for compatibility with wine */
    user_sid = _pyi_win32_get_sid(TokenUser);

    /* If program is running within an AppContainer, the app container SID has to be added to
     * the DACL, otherwise our process will not have access to the temporary directory. */
    app_container_sid = _pyi_win32_get_sid(TokenAppContainerSid); /* NULL when not running in AppContainer */

    /* DACL descriptor D:dacl_flags(string_ace1)(string_ace2)
     * with ACE string:
     * ace_type;ace_flags;rights;object_guid;inherit_object_guid;account_sid;(resource_attribute)
     * - ace_type = SDDL_ACCESS_ALLOWED (A)
     * - rights = SDDL_FILE_ALL (FA)
     * - account_sid = current user (queried SID)
     */
    if (app_container_sid) {
        ret = _snwprintf(
            security_descriptor_str,
            PYI_PATH_MAX,
            L"D:(A;;FA;;;%s)(A;;FA;;;%s)",
            user_sid ? user_sid : L"S-1-3-4",
            app_container_sid);
    } else {
        ret = _snwprintf(
            security_descriptor_str,
            PYI_PATH_MAX,
            L"D:(A;;FA;;;%s)",
            user_sid ? user_sid : L"S-1-3-4");
    }

    LocalFree(user_sid); /* Must be freed using LocalFree() */
    LocalFree(app_container_sid); /* Must be freed using LocalFree() */

    if (ret >= PYI_PATH_MAX) {
        PYI_WARNING_W(L"Security descriptor string length exceeds PYI_PATH_MAX!\n");
        return NULL;
    }

    /* Convert security descriptor string to security descriptor, and
     * store it in the SECURITY_ATTRIBUTES structure. */
    PYI_DEBUG_W(L"LOADER: initializing security descriptor from string: %ls\n", security_descriptor_str);
    ret = ConvertStringSecurityDescriptorToSecurityDescriptorW(
        security_descriptor_str,
        SDDL_REVISION_1,
        &lpSecurityDescriptor,
        NULL);
    if (ret == 0) {
        return NULL;
    }

    /* Allocate SECURITY_ATTRIBUTES and fill it in. */
    security_attr = calloc(1, sizeof(SECURITY_ATTRIBUTES));
    security_attr->nLength = sizeof(SECURITY_ATTRIBUTES);
    security_attr->bInheritHandle = FALSE;
    security_attr->lpSecurityDescriptor = lpSecurityDescriptor;

    return security_attr;
}

/* Free security descriptor applied to application's temporary directory and its
 * sub-directories.
 */
void
pyi_win32_free_security_descriptor(SECURITY_ATTRIBUTES **security_attr_ref)
{
    SECURITY_ATTRIBUTES *security_attr = *security_attr_ref;

    security_attr_ref = NULL;

    /* Free security descriptor */
    LocalFree(security_attr->lpSecurityDescriptor);

    /* Free the structure itself */
    free(security_attr);
}


/**********************************************************************\
 *      Console minimization/hiding (console-enabled build only)      *
\**********************************************************************/
#if !defined(WINDOWED)

/* Helper that hides or minimizes the console window if it is owned by
 * the process. The show_cmd argument is passed to the ShowWindow call,
 * and should be either SW_HIDE or SW_SHOWMINNOACTIVE.
 */
static void pyi_win32_adjust_console(int show_cmd)
{
    HWND hConsole = GetConsoleWindow();
    if (hConsole != NULL) {
        DWORD dwProcessId = GetCurrentProcessId();
        DWORD dwConsoleProcessId;
        int i;

        if (GetWindowThreadProcessId(hConsole, &dwConsoleProcessId) == 0) {
            return; /* Window handle is invalid */
        }

        if (dwProcessId != dwConsoleProcessId) {
            /* We do not own console window (i.e., were launched from existing console) */
            PYI_DEBUG_W(L"LOADER: console window not owned by application - skipping adjustment.\n");
            return;
        }

        PYI_DEBUG_W(L"LOADER: console window is owned by application - calling ShowWindow() with nCmdShow=%d...\n", show_cmd);

        /* If Windows Terminal is used as the default terminal app (which
         * is the case on contemporary Windows 11 systems), we need to
         * ensure that its window was shown before we submit request
         * to hide/minimize it (sidenote: both translate into minimization).
         * Otherwise, the request ends up being ignored. ShowWindow()
         * returns the previous status of the window; non-zero if it
         * was visible, zero if it was not visible - use that to catch
         * transition from visible state. As a safety mechanism, perform
         * up to five attempts with 100 ms delay, so that in the worst
         * case, we end up delaying the program by half a second. */
        for (i = 0; i < 5; i++) {
            BOOL status;

            status = ShowWindow(hConsole, show_cmd);
            if (status != 0) {
                PYI_DEBUG_W(L"LOADER: console window transitioned from non-hidden to hidden on attempt #%i.\n", i + 1);
                return;
            }
            Sleep(100);
        }

        PYI_DEBUG_W(L"LOADER: console window failed to transition from non-hidden to hidden in %i attempts!\n", i);
    }
}

void pyi_win32_hide_console()
{
    pyi_win32_adjust_console(SW_HIDE);
}

void pyi_win32_minimize_console()
{
    pyi_win32_adjust_console(SW_SHOWMINNOACTIVE);
}

#endif /* !defined(WINDOWED) */


/**********************************************************************\
 *      Force-unload of bundled DLLs from onefile parent process      *
\**********************************************************************/
/* Our last resort in ensuring that onefile application can clean up
 * its temporary directory... */
static int
_pyi_win32_force_unload_bundled_dlls(const struct PYI_CONTEXT *pyi_ctx)
{
    HANDLE process_handle;
    HMODULE *loaded_dlls = NULL;
    DWORD loaded_dlls_size = 0;
    int num_dlls;
    int num_problematic_dlls;
    int num_unloaded_dlls = 0;
    wchar_t dll_filename[PYI_PATH_MAX];
    wchar_t application_home_dir[PYI_PATH_MAX];
    size_t application_home_dir_len;
    int i;

    process_handle = GetCurrentProcess(); /* Psedo-handle; does not need to be closed */

    /* Query the required size for lpModules */
    if (EnumProcessModules(process_handle, loaded_dlls, 0, &loaded_dlls_size) == 0) {
        return 0; /* Technically an error, but treat it as if no DLLs were unloaded. */
    }
    if (loaded_dlls_size <= 0) {
        return 0;
    }

    /* Allocate the array */
    loaded_dlls = calloc(loaded_dlls_size, 1);
    if (!loaded_dlls) {
        return 0;
    }

    /* Read the loaded DLLs handles into array */
    if (EnumProcessModules(process_handle, loaded_dlls, loaded_dlls_size, &loaded_dlls_size) == 0) {
        goto cleanup;
    }

    /* Convert the application's temporary directory path to wide-char
     * for path comparison */
    if (!pyi_win32_utf8_to_wcs(pyi_ctx->application_home_dir, application_home_dir, PYI_PATH_MAX)) {
        goto cleanup;
    }
    application_home_dir_len = wcslen(application_home_dir);

    /* Go over loaded DLLs; display them for debug purposes, and identify
     * the ones that originate from application's top level directory.
     * The handles of such DLLs are pushed to the beginning of the
     * array, so that we can iterate over problematic DLLs in subsequent
     * loop. */
    num_dlls = loaded_dlls_size / sizeof(HMODULE);
    num_problematic_dlls = 0;
    PYI_DEBUG_W(L"LOADER: found %d loaded DLLs...\n", num_dlls);
    for (i = 0; i < num_dlls; i++) {
        /* Query the DLL filename */
        if (GetModuleFileNameExW(process_handle, loaded_dlls[i], dll_filename, PYI_PATH_MAX) == 0) {
            PYI_DEBUG_W(L"LOADER: could not resolve DLL's name - skipping!\n");
            continue;
        }
        PYI_DEBUG_W(L"LOADER: loaded DLL: %ls\n", dll_filename);

        /* Check if the DLL comes from application's top-level directory */
        if (_wcsnicmp(application_home_dir, dll_filename, application_home_dir_len) == 0) {
            loaded_dlls[num_problematic_dlls++] = loaded_dlls[i]; /* Move to start of array */
        }
    }

    PYI_DEBUG_W(L"LOADER: found %d DLL(s) loaded from application's temporary directory!\n", num_problematic_dlls);
    for (i = 0; i < num_problematic_dlls; i++) {
        int num_attempts = 0;

        /* Query the DLL filename - a failure here indicates that the DLL
         * might have been unloaded as result of force-unloading another
         * DLL... */
        if (GetModuleFileNameExW(process_handle, loaded_dlls[i], dll_filename, PYI_PATH_MAX) == 0) {
            PYI_DEBUG_W(L"LOADER: could not resolve DLL's name (was it unloaded?) - skipping!\n");
            continue;
        }

        /* Keep calling FreeLibrary() until it fails - which hopefully
         * means that the offending DLL is gone for good. */
        while (1) {
            num_attempts++;
            PYI_DEBUG_W(L"LOADER: forcing unload of %ls (attempt #%d)\n", dll_filename, num_attempts);
            if (FreeLibrary(loaded_dlls[i]) == 0) {
                PYI_DEBUG_W(L"LOADER: DLL unloaded after %d attempt(s)!\n", num_attempts);
                num_unloaded_dlls++;
                break;
            }
            /* Make sure we don't loop forever, just in case. */
            if (num_attempts >= 32) {
                PYI_DEBUG_W(L"LOADER: giving up after %d attempts!\n", num_attempts);
                break;
            }
        }
    }

cleanup:
    free(loaded_dlls);

    return num_unloaded_dlls;
}

int pyi_win32_mitigate_locked_temporary_directory(const struct PYI_CONTEXT *pyi_ctx)
{
    int num_unloaded_dlls;
    int cleanup_status = -1;

    const int max_attempts = 15; /* Maximum number of attempts in retry loop */
    const int delay = 1000; /* Delay for retry loop (milliseconds) */
    int attempt_count;

    /* One reason for locked files in the temporary directory might be
     * due to Tcl/Tk shared libs pulling in dependencies and failing to
     * release them when they are unloaded. This happens in frozen
     * applications that use splash screen, where Tcl/Tk needs to be
     * loaded in the parent process of the onefile application.
     *
     * For example, tcl86.dll from mingw-w64-i686-tcl 8.6.12-3 (32-bit
     * msys2/mingw32 environment) pulls in libgcc_s_dw2-1.dll and
     * libwinpthread-1.dll, and does not unload them when it is unloaded.
     * Similar situation was observed in 64-bit builds with UPX-processed
     * Tcl/Tk DLLs, which leak VCRUNTIME140.dll (although this is mitigated
     * separately by pre-load of system copy, if available) and/or ZLIB1.dll.
     *
     * So we go over DLLs loaded in the process, find the ones that
     * originate from the application's temporary directory, and try
     * to force-unload them, before repeating the directory removal
     * attempt. Force-unloading DLLs is risky and might crash the process,
     * but at this point, we have nothing left to lose... */
    PYI_DEBUG_W(L"LOADER: trying to force-unload bundled DLLs from this process...\n");
    num_unloaded_dlls = _pyi_win32_force_unload_bundled_dlls(pyi_ctx);
    if (num_unloaded_dlls > 0) {
        PYI_DEBUG_W(L"LOADER: unloaded %d bundled DLL(s) from this process - trying to remove temporary directory again...\n", num_unloaded_dlls);
        cleanup_status = pyi_recursive_rmdir(pyi_ctx->application_home_dir);
        if (cleanup_status == 0) {
            PYI_DEBUG_W(L"LOADER: removal succeeded.\n");
            return 0;
        } else {
            PYI_DEBUG_W(L"LOADER: removal failed!\n");
        }
    } else {
        PYI_DEBUG_W(L"LOADER: no bundled DLLs were unloaded from this process.\n");
    }

    /* Sometimes, the spawned grandchild processes need a bit more time to
     * completely finish; if their executable is part of the frozen
     * application, it and its bundled dependencies will still be locked
     * at this point. This seems to happen, for example, with the
     * QtWebEngineProcess.exe helper when running a QtWebEngine-based
     * application on a system with high CPU load.
     *
     * Other times, it might be Windows itself getting in our way; it seems
     * that when running an x86_64 frozen application on an arm64 system,
     * the OS ends up locking (some of?) the python extensions and DLLs
     * for a short while; see #8837. The same issue has also been observed
     * on x86_64; see #8866.
     *
     * The retry loop below attempts to address this. */
    attempt_count = 0;
    while (attempt_count++ < max_attempts) {
        PYI_DEBUG_W(L"LOADER: waiting %d milliseconds before trying to remove temporary directory again...\n", delay);
        Sleep(delay);
        PYI_DEBUG_W(L"LOADER: trying to remove temporary directory (attempt %d / %d)...\n", attempt_count, max_attempts);
        cleanup_status = pyi_recursive_rmdir(pyi_ctx->application_home_dir);
        if (cleanup_status == 0) {
            PYI_DEBUG_W(L"LOADER: removal succeeded.\n");
            return 0;
        } else {
            PYI_DEBUG_W(L"LOADER: removal failed!\n");
        }
    }
    PYI_DEBUG_W(L"LOADER: given up after %d attempts!\n", max_attempts);

    /* Well, tough luck. */
    return -1;
}


#endif /* ifdef _WIN32 */
