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

/*
 * Additional security verification of inherited run-time environment.
 */

#ifdef _WIN32
    #include <windows.h>
    #include <tlhelp32.h> /* CreateToolhelp32Snapshot(), Process32FirstW(), Process32NextW() */
#else
    #include <sys/stat.h> /* struct stat */
    #include <unistd.h> /* readlink() */
#endif

#include <stdio.h>  /* snprintf() */
#include <string.h>  /* strcmp() */

#if defined(__APPLE__)
    #include <libproc.h> /* proc_pidpath() */
#endif

#include "pyi_global.h"
#include "pyi_main.h"
#include "pyi_path.h"
#include "pyi_utils.h"


/**********************************************************************\
 *                   Verification of parent process                   *
\**********************************************************************/
/* Verify that parent process uses same executable as current process.
 * This aims to ensure that the run-time environment was indeed inherited
 * from a parent process of a onefile application, rather than being
 * spoofed by malicious user. */

#if defined(_WIN32)

static int
_pyi_security_verify_parent_proces_win32(const struct PYI_CONTEXT *pyi_ctx)
{
    DWORD pid;
    DWORD ppid;

    HANDLE process_snapshot;
    PROCESSENTRY32W process_entry;
    BOOL entry_found;

    HANDLE process_handle;
    wchar_t parent_executable_w[PYI_PATH_MAX];
    char parent_executable[PYI_PATH_MAX];
    DWORD parent_executable_length;

    /* Current process ID, for look-up in the process snapshot */
    pid = GetCurrentProcessId();

    /* Take the process snapshot */
    process_snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (process_snapshot == INVALID_HANDLE_VALUE) {
        PYI_ERROR_W(L"Security validation failure: could not obtain process snapshot!\n");
        return -1;
    }

    /* Walk the process snapshot to find entry for our process, and get
     * parent process ID from it. */
    process_entry.dwSize = sizeof(PROCESSENTRY32);
    if (!Process32FirstW(process_snapshot, &process_entry)) {
        PYI_ERROR_W(L"Security validation failure: could not walk the process snapshot!\n");
        CloseHandle(process_snapshot);
        return -1;
    }

    entry_found = FALSE;
    do {
        if (process_entry.th32ProcessID == pid) {
            ppid = process_entry.th32ParentProcessID;
            entry_found = TRUE;
            break;
        }
    } while(Process32NextW(process_snapshot, &process_entry));

    CloseHandle(process_snapshot);

    if (!entry_found) {
        PYI_ERROR_W(L"Security validation failure: could not determine parent process ID!\n");
        return -1;
    }

    /* Now try to query process for its executable name.
     * QueryFullProcessImageNameW() seems to return a fully-resolved
     * path to the executable, even when the parent process is launched
     * via symbolic link. */
    process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, ppid);
    if (process_handle == INVALID_HANDLE_VALUE) {
        PYI_ERROR_W(L"Security validation failure: failed to obtain information about parent proces!\n");
        return -1;
    }

    parent_executable_length = PYI_PATH_MAX;
    if (!QueryFullProcessImageNameW(process_handle, 0, parent_executable_w, &parent_executable_length)) {
        PYI_ERROR_W(L"Security validation failure: failed to obtain executable path for parent proces!\n");
        CloseHandle(process_handle);
        return -1;
    }

    CloseHandle(process_handle);

    PYI_DEBUG_W(L"SECURITY: parent process executable: %ls\n", parent_executable_w);

    /* Convert to UTF-8 for comparison */
    if (!pyi_win32_wcs_to_utf8(parent_executable_w, parent_executable, PYI_PATH_MAX)) {
        PYI_ERROR_W(L"Security validation failure: failed to convert parent process executable path to UTF-8!\n");
        return -1;
    }

    /* Ensure that same executable is used */
    if (strcmp(parent_executable, pyi_ctx->executable_filename) != 0) {
        PYI_ERROR_W(L"Security validation failure: parent process has different executable!\n");
        return -1;
    }

    return 0;
}

#elif defined(__APPLE__)

static int
_pyi_security_verify_parent_proces_macos(const struct PYI_CONTEXT *pyi_ctx)
{
    /* Try to look up the executable of the parent process - it should
     * be the same as that of the current process. */
    pid_t ppid;
    char parent_executable[PYI_PATH_MAX];

    /* Get parent PID and corresponding executable name. proc_pidpath()
     * seems to return a fully-resolved path to the executable, even
     * when the parent process was launched via symbolic link. */
    ppid = getppid();
    proc_pidpath(ppid, parent_executable, sizeof(parent_executable));

    PYI_DEBUG("SECURITY: parent process executable: %s\n", parent_executable);

    /* Ensure that same executable is used */
    if (strcmp(parent_executable, pyi_ctx->executable_filename) != 0) {
        PYI_ERROR("Security validation failure: parent process has different executable!\n");
        return -1;
    }

    return 0;
}

#else

static int
_pyi_security_verify_parent_proces_posix(const struct PYI_CONTEXT *pyi_ctx)
{
    /* Try to look up the executable of the parent process - it should
     * be the same as that of the current process. */
    pid_t ppid;
    ssize_t name_len = -1;
    char proc_path[PYI_PATH_MAX];
    char parent_executable[PYI_PATH_MAX];

#if defined(__linux__) || defined(__CYGWIN__)
    const char *proc_path_fmt = "/proc/%d/exe";
#elif defined(__FreeBSD__)
    const char *proc_path_fmt = "/proc/%d/file";
#elif defined(__sun)
    const char *proc_path_fmt = "/proc/%d/path/a.out";
#else
    const char *proc_path_fmt = NULL;
#endif

    /* Handle unsupported POSIX platforms, where we have no way to look up
     * the parent executable. Disallow setuid-enabled executables, otherwise
     * skip the check. */
    if (!proc_path_fmt) {
        if (pyi_ctx->has_setuid) {
            PYI_ERROR("Security validation failure: setuid-enabled executables are not supported on this platform!\n");
            return -1;
        } else {
            PYI_DEBUG("SECURITY: unsupported platform - skipping check for non-setuid executable!\n");
            return 0;
        }
    }

    /* Get parent PID */
    ppid = getppid();

    /* Try to look up the /proc entry. The entry points at "true" file
     * location, i.e., fully canonicalized and with all symbolic links
     * resolved. */
    if (snprintf(proc_path, PYI_PATH_MAX, proc_path_fmt, ppid) >= PYI_PATH_MAX) {
        PYI_ERROR("Security validation failure: could not format /proc entry path!\n");
        return -1;
    }

    name_len = readlink(proc_path, parent_executable, PYI_PATH_MAX - 1);
    if (name_len == -1) {
        PYI_ERROR("Security validation failure: could not determine the executable path for parent process!\n");
        return -1;
    }

    /* Output is not yet NULL-terminated, so we need to do it using returned byte count. */
    parent_executable[name_len] = 0;

    PYI_DEBUG("SECURITY: parent process executable: %s\n", parent_executable);

    /* Ensure that same executable is used */
    if (strcmp(parent_executable, pyi_ctx->executable_filename) != 0) {
        PYI_ERROR("Security validation failure: parent process has different executable!\n");
        return -1;
    }

    return 0;
}

#endif


int
pyi_security_verify_parent_proces(const struct PYI_CONTEXT *pyi_ctx)
{
    PYI_DEBUG("SECURITY: verifying parent process...\n");

    /* Use OS-specific implementation */
#if defined(_WIN32)
    return _pyi_security_verify_parent_proces_win32(pyi_ctx);
#elif defined(__APPLE__)
    return _pyi_security_verify_parent_proces_macos(pyi_ctx);
#else
    return _pyi_security_verify_parent_proces_posix(pyi_ctx);
#endif
}


/**********************************************************************\
 *            Verification of application's home directory            *
\**********************************************************************/
/* Verify the application's top-level / home directory.
 *
 * In onefile mode, check that the directory's name matches the format
 * used by PyInstaller's bootloader.
 *
 * On POSIX platforms, perform additional check for executables with
 * setuid bit set; in that case, we require:
 *  - the owner ID of the top-level application directory to match the
 *    effective user ID
 *  - permissions on the top-level application directory to be set to
 *    0700
 *
 * This should be ensure that the onefile child processes are inheriting
 * temporary application directory that was set up by the onefile parent
 * process (instead of being passed an arbitrary directory as top-level
 * application directory via spoofed environment variables). Similarly,
 * it should ensure that setuid-enabled onedir executable has an
 * accompanying contents directory that cannot be modified by a
 * non-privileged user. */
#if !defined(_WIN32) && !defined(__APPLE__)

static int
pyi_security_verify_application_home_dir_permissions(const struct PYI_CONTEXT *pyi_ctx)
{
    uid_t euid;
    uid_t permissions;
    struct stat application_home_dir_stat;

    /* Applicable only to executables with setuid bit set. */
    if (!pyi_ctx->has_setuid) {
        PYI_DEBUG("SECURITY: setuid bit is not set - skipping verification of owner/permissions of application's home directory.\n");
        return 0;
    }

    PYI_DEBUG("SECURITY: setuid bit is set - verifying owner/permissions of application's home directory...\n");

    if (stat(pyi_ctx->application_home_dir, &application_home_dir_stat) < 0) {
        PYI_ERROR("Security validation failure: could not stat() the application's home directory!\n");
        return -1;
    }

    /* Ensure that owner ID of application's temporary directory matches
     * the effective user ID. By comparing effective user ID instead of
     * executable's owner ID, we attempt to accommodate scenario where a
     * setuid-enabled application drops its privileges and attempts to
     * spawn a worker subprocess. Note that this requires that the
     * application transfers the ownership of its temporary directory
     * prior to privilege drop; but this is the case anyway, otherwise
     * it would end up locking both itself and its worker subprocesses
     * out of the temporary directory... */
    euid = geteuid();
    if (application_home_dir_stat.st_uid != euid) {
        PYI_ERROR(
            "Security validation failure: owner ID of application's home directory (%d) does not match the effective user ID (%d)!\n",
            application_home_dir_stat.st_uid, euid
        );
        return -1;
    }

    /* Ensure that the application's home directory has permissions used
     * by bootloader when creating ephemeral application directory
     * (i.e., S_IRWXU = 0700). In case of onedir application, it ensures
     * that the contents directory cannot be modified by unprivileged
     * user. */
    permissions = application_home_dir_stat.st_mode & (S_IRWXU | S_IRWXG | S_IRWXO);
    if (permissions != S_IRWXU) {
        PYI_ERROR("Security validation failure: application's home directory has invalid permissions (0%o)!\n", permissions);
        return -1;
    }

    return 0;
}

#endif


int
pyi_security_verify_application_home_dir(const struct PYI_CONTEXT *pyi_ctx, unsigned int prefix_pid)
{
    /* In onefile mode, the application home directory name should have
     * distrinct, PyInstaller-specific format: _MEIXXXXXX */
    if (pyi_ctx->is_onefile) {
        char basename[PYI_PATH_MAX];
        size_t name_len;

        char expected_prefix[32];
        int expected_prefix_len;

        if (!pyi_path_basename(basename, pyi_ctx->application_home_dir)) {
            PYI_ERROR("Security validation failure: failed to obtain name of application's home directory!\n");
            return -1;
        }

        PYI_DEBUG("SECURITY: verifying the name of application's home directory (%s)...\n", basename);

        /* Verify the length of the name:
         *  - Windows: _MEI + process ID number (%08x format) + suffix
         *    added by _wtempnam(); so we check that the name is at least
         *    12 characters long...
         *  - other platforms: _MEI + process ID number (%08x format) +
         *    six random characters added by mkdtemp(); so we check that
         *    the name is exactly 18 characters long... */
        name_len = strlen(basename);

#ifdef _WIN32
        if (name_len < 12) {
            PYI_ERROR("Security validation failure: unexpected name of application's home directory!\n");
            return -1;
        }
#else
        if (name_len != 18) {
            PYI_ERROR("Security validation failure: unexpected name of application's home directory!\n");
            return -1;
        }
#endif

        /* Verify the prefix */
        if (prefix_pid > 0) {
            expected_prefix_len = snprintf(expected_prefix, 32, "_MEI%08x", prefix_pid);
        } else {
            expected_prefix_len = snprintf(expected_prefix, 32, "_MEI");
        }
        if (expected_prefix_len < 0 || expected_prefix_len >= 32) {
            PYI_ERROR("Security validation failure: failed to format expected name prefix!\n");
            return -1;
        }

        PYI_DEBUG("SECURITY: expected prefix: %s\n", expected_prefix);

        if (strncmp(basename, expected_prefix, expected_prefix_len) != 0) {
            PYI_ERROR("Security validation failure: unexpected name of application's home directory!\n");
            return -1;
        }
    }

    /* POSIX: additional owner/permissions validation when setuid bit is
     * set on the executable */
#if !defined(_WIN32) && !defined(__APPLE__)
    if (pyi_security_verify_application_home_dir_permissions(pyi_ctx) < 0) {
        return -1;
    }
#endif

    return 0;
}
