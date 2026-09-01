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
    #include <unistd.h> /* getppid(), geteuid() */
    #include <fcntl.h>
    #include <errno.h>
#endif

#include <stdio.h>  /* snprintf() */
#include <string.h>  /* strcmp() */
#include <stdlib.h>  /* realpath() */

#if defined(__APPLE__)
    #include <libproc.h> /* proc_pidpath() */
#endif

#include "pyi_global.h"
#include "pyi_main.h"
#include "pyi_path.h"
#include "pyi_utils.h"



/**********************************************************************\
 *      Early check for availability of parent-process validation     *
\**********************************************************************/
/* Check whether parent-process validation is available on this platform
 * (strictly required for setuid-enabled onefile executables), so we can
 * raise an early error on known unsupported platforms.
 *
 * For details about constraints see platform-specific implementations
 * of validation helpers below. */
bool
pyi_security_onefile_parent_verification_available()
{
#if defined(_WIN32)
    return true;
#elif defined(__APPLE__)
    return true;
#elif defined(__linux__) || defined(__CYGWIN__) || defined(__NetBSD__)
    return true;
#elif defined(__FreeBSD__)
    /* Supported only if /proc is available. */
    struct stat curproc_dir_stat;
    if (stat("/proc/curproc", &curproc_dir_stat) < 0) {
        PYI_ERROR("Security validation failure: setuid-enabled executables are not supported on this system (missing /proc)!\n");
        return false;
    }
    return true;
#elif defined(__sun)
    return true;
#else
    /* Other POSIX platforms are unsupported due to lack of required
     * information in /proc */
    PYI_ERROR("Security validation failure: setuid-enabled executables are not supported on this platform!\n");
    return false;
#endif
}


/**********************************************************************\
 *                 Verification of parent-process PID                 *
\**********************************************************************/
/* Verify that the given process ID of originating onefile parent process
 * (extracted from the _MEI directory name) matches the process ID of
 * the parent process of this process, or one of its ancestor processes. */

#define PYI_MAX_PROCESS_TREE_DEPTH 128

struct PYI_PROCESS_LINEAGE_TRACKER
{
    /* Keep track of seen ancestor PIDs, in order to prevent endless
     * loop caused by re-use of process IDs. */
    size_t ancestor_count;
    unsigned int ancestor_pids[PYI_MAX_PROCESS_TREE_DEPTH];

    /* Lowest valid PID value (platform-specific) */
    unsigned int lowest_valid_pid;

    /* Process snapshot (Windows) */
#if defined(_WIN32)
    HANDLE process_snapshot;
    PROCESSENTRY32W process_entry;
#endif
};

/* Initialize the platform-specific parts of the auxiliary structure */
static int
pyi_process_lineage_tracker_init(struct PYI_PROCESS_LINEAGE_TRACKER *tracker)
{
#if defined(_WIN32)
    /* Take the process snapshot */
    tracker->process_snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (tracker->process_snapshot == INVALID_HANDLE_VALUE) {
        PYI_ERROR_W(L"Security validation failure: could not obtain process snapshot!\n");
        return -1;
    }

    /* Initialize the process entry structure */
    tracker->process_entry.dwSize = sizeof(PROCESSENTRY32W);
#endif

    /* Initialize ancestor counter (= current depth of process tree) */
    tracker->ancestor_count = 0;

    /* Platform-specific lowest valid PID.
     * On Windows, lowest PID is 4 (System).
     * On POSIX systems, lowest PID is 1 (init). */
#if defined(_WIN32)
    tracker->lowest_valid_pid = 4;
#else
    tracker->lowest_valid_pid = 1;
#endif

    return 0;
}

/* Clean-up the platform-specific parts of the auxiliary structure */
static void
pyi_process_lineage_tracker_cleanup(struct PYI_PROCESS_LINEAGE_TRACKER *tracker)
{
#if defined(_WIN32)
    CloseHandle(tracker->process_snapshot);
#else
    (void)tracker;
#endif
}

/* Add the given process ID to the list of seen ancestor process IDs,
 * and ensure that maximum allowed process-tree depth has not yet been
 * reached. */
static int
pyi_process_lineage_tracker_add_ancestor(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int ancestor_pid)
{
    if (tracker->ancestor_count + 1 >= PYI_MAX_PROCESS_TREE_DEPTH) {
        PYI_ERROR("Security validation failure: maximum process tree depth exceeded!\n");
        return false;
    }
    tracker->ancestor_pids[tracker->ancestor_count++] = ancestor_pid;
    return true;
}

/* Check whether the given ancestor PID has already been encountered
 * before (was registered by pyi_process_lineage_tracker_add_ancestor()). */
static bool
pyi_process_lineage_tracker_check_ancestor_seen(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int ancestor_pid)
{
    size_t i;
    for (i = 0; i < tracker->ancestor_count; i++) {
        if (tracker->ancestor_pids[i] == ancestor_pid) {
            return true;
        }
    }
    return false;
}

/* Find parent-process ID for the process identified by the given process
 * ID. Uses platform-specific mechanism for looking up information about
 * the given process. */
#if defined(_WIN32)

static int
pyi_process_lineage_tracker_get_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int target_pid, unsigned int *parent_pid)
{
    /* Walk the process snapshot to find the entry for target_pid */
    if (!Process32FirstW(tracker->process_snapshot, &tracker->process_entry)) {
        PYI_ERROR_W(L"Security validation failure: could not walk the process snapshot!\n");
        return -1;
    }

    do {
        if (tracker->process_entry.th32ProcessID == target_pid) {
            *parent_pid = tracker->process_entry.th32ParentProcessID;
            PYI_DEBUG_W(L"SECURITY: parent of %u is %u (%ls)\n", target_pid, *parent_pid, tracker->process_entry.szExeFile);
            return 0;
        }
    } while (Process32NextW(tracker->process_snapshot, &tracker->process_entry));

    /* Not found; let caller handle that */
    *parent_pid = 0;
    return 0;
}

#elif defined(__APPLE__)

static int
pyi_process_lineage_tracker_get_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int target_pid, unsigned int *parent_pid)
{
    struct proc_bsdshortinfo info;

    if (proc_pidinfo(target_pid, PROC_PIDT_SHORTBSDINFO, 0, &info, sizeof(info)) != sizeof(info)) {
        PYI_ERROR("Security validation failure: could not look up ancestor process info!\n");
        return -1;
    }
    *parent_pid = info.pbsi_ppid;

    return 0;
}

#else /* All other POSIX platforms */

#if defined(__linux__) || defined(__CYGWIN__) || defined(__NetBSD__) || defined(__FreeBSD__) || defined(__sun)

/* Read contents of a /proc file into given buffer */
static size_t
_read_proc_file(const char *filename, unsigned char *buffer, size_t buflen)
{
    unsigned char *bufptr = buffer;
    size_t to_read = buflen;
    size_t ret;
    int fd;

    fd = open(filename, O_RDONLY | O_NOFOLLOW);
    if (fd == -1) {
        return -1;
    }

    while (to_read > 0) {
        ret = read(fd, bufptr, to_read);
        if (ret < 0) {
            if (errno == EAGAIN || errno == EINTR) {
                continue;
            } else {
                close(fd);
                return -1;
            }
        } else if (ret == 0) {
            break; /* end of file */
        }

        to_read -= ret;
        bufptr += ret;
    }

    close(fd);

    return (size_t)(bufptr - buffer);
}

#endif /* defined(__linux__) || defined(__CYGWIN__) || defined(__NetBSD__) || defined(__FreeBSD__) || defined(__sun) */

#if defined(__linux__) || defined(__CYGWIN__) || defined(__NetBSD__)

static int
pyi_process_lineage_tracker_get_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int target_pid, unsigned int *parent_pid)
{
    /* As per "man proc_pid_stat", the /proc/pid/stat file contains
     * space-delimited fields:
     * pid (%d), (comm) (%s), state (%c), ppid (%d), ...
     *
     * Unfortunately, the process name (comm) can contain a whitespace or
     * even a newline, which precludes direct parsing with sscanf(). Instead,
     * we read the beginning of the file, scan for the closing brace, and
     * then parse the state and ppid part using sscanf().
     *
     * We read first 48 bytes; pid is a 32-bit integer (max 10 characters), comm
     * is max 15 characters plus enclosing braces, state is a single-character
     * flag, and ppid is 32-bit integer. */
    char proc_path[PYI_PATH_MAX];
    char buffer[48];
    size_t ret;
    size_t pos;

    (void)tracker;

    if (snprintf(proc_path, 4096, "/proc/%u/stat", target_pid) >= PYI_PATH_MAX) {
        PYI_ERROR("Security validation failure: could not format /proc/pid/stat path!\n");
        return -1;
    }

    ret = _read_proc_file(proc_path, (unsigned char *)buffer, sizeof(buffer));
    if (ret != sizeof(buffer)) {
        PYI_ERROR("Security validation failure: could not read from /proc/pid/stat!\n");
        return -1;
    }
    buffer[ret - 1] = 0;

    /* Search for closing brace */
    for (pos = ret; pos >= 0; pos--) {
        if (buffer[pos] == ')') {
            break;
        }
    }
    if (pos < 0) {
        PYI_ERROR("Security validation failure: could not parse /proc/pid/stat!\n");
        return -1;
    }

    /* Extract ppid */
    if (sscanf(buffer + pos, ") %*c %u ", parent_pid) != 1) {
        PYI_ERROR("Security validation failure: could not parse /proc/pid/stat!\n");
        return -1;
    }

    return 0;
}

#elif defined(__FreeBSD__)

static int
pyi_process_lineage_tracker_get_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int target_pid, unsigned int *parent_pid)
{
    /* /proc/pid/status seem to contain whitespace-delimited fields,
     * with first three being: process name, pid, and ppid. Characters
     * such as whitespace in process name are escaped using octal sequence
     * (e.g., \040). It seems that up to 19 characters are included,
     * but presumably all could be octal escape sequences; so the buffer
     * needs to account for max. 76 characters in the process name alone. */
    char proc_path[PYI_PATH_MAX];
    char buffer[128];
    size_t ret;

    (void)tracker;

    if (snprintf(proc_path, PYI_PATH_MAX, "/proc/%u/status", target_pid) >= PYI_PATH_MAX) {
        PYI_ERROR("Security validation failure: could not format /proc/pid/status path!\n");
        return -1;
    }

    /* Depending on process name, fewer than 128 bytes might be read, so
     * do not enforce expected length. But expect at least one byte to
     * have been read... */
    ret = _read_proc_file(proc_path, (unsigned char *)buffer, sizeof(buffer));
    if (ret <= 0) {
        PYI_ERROR("Security validation failure: could not read from /proc/pid/status!\n");
        return -1;
    }
    buffer[ret - 1] = 0;

    /* Extract ppid */
    if (sscanf(buffer, "%*s %*d %u ", parent_pid) != 1) {
        PYI_ERROR("Security validation failure: could not parse /proc/pid/status!\n");
        return -1;
    }

    return 0;
}

#elif defined(__sun)

static int
pyi_process_lineage_tracker_get_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int target_pid, unsigned int *parent_pid)
{
    /* Read first four 32-bit integer fields from /proc/pid/psinfo:
     * pr_flag, pr_nlwp, pr_pid, pr_ppid. We could also use struct
     * psinfo_t from /usr/include/sys/procfs.h */
    char proc_path[PYI_PATH_MAX];
    unsigned char buffer[16];
    size_t ret;

    if (snprintf(proc_path, PYI_PATH_MAX, "/proc/%u/psinfo", target_pid) >= PYI_PATH_MAX) {
        PYI_ERROR("Security validation failure: could not format /proc/pid/psinfo path!\n");
        return -1;
    }

    ret = _read_proc_file(proc_path, buffer, sizeof(buffer));
    if (ret != sizeof(buffer)) {
        PYI_ERROR("Security validation failure: could not read from /proc/pid/psinfo!\n");
        return -1;
    }
    *parent_pid = *(unsigned int *)(buffer + 12); /* Presumably native endianness is used */

    return 0;
}

#else

static int
pyi_process_lineage_tracker_get_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, const unsigned int target_pid, unsigned int *parent_pid)
{
    (void)tracker;
    (void)target_pid;
    (void)parent_pid;
    PYI_ERROR("Security validation failure: parent-process ID validation is not supported on this platform!\n");
    return -1;
}

#endif /* defined(__linux__) || defined(__CYGWIN__) || defined(__NetBSD__) */

#endif /* defined(_WIN32) */


/* Get process ID for the immediate parent process of the current process.
 * On POSIX platforms, this wraps the getppid() system call. On Windows,
 * we need to walk the process snapshot, same as for arbitrary target
 * process. */
static int
pyi_process_lineage_tracker_get_immediate_parent_pid(struct PYI_PROCESS_LINEAGE_TRACKER *tracker, unsigned int *parent_pid)
{
#if defined(_WIN32)
    return pyi_process_lineage_tracker_get_parent_pid(tracker, GetCurrentProcessId(), parent_pid);
#else
    (void)tracker;
    *parent_pid = getppid();
    return 0;
#endif
}


bool
pyi_security_verify_onefile_parent_pid(const struct PYI_CONTEXT *pyi_ctx, const unsigned int onefile_parent_pid, const bool search_process_tree)
{
    struct PYI_PROCESS_LINEAGE_TRACKER tracker;
    unsigned int current_pid;
    unsigned int parent_pid;
    bool succeeded = false;

    PYI_DEBUG("SECURITY: verifying process ID of originating onefile parent process (%u)...\n", onefile_parent_pid);

    /* Initialize the auxiliary tracker structure. */
    if (pyi_process_lineage_tracker_init(&tracker) < 0) {
        goto end;
    }

    /* Get process ID of immediate parent process. */
    if (pyi_process_lineage_tracker_get_immediate_parent_pid(&tracker, &parent_pid) < 0) {
        goto end;
    }
    PYI_DEBUG("SECURITY: parent process ID of current process: %u\n", parent_pid);

    if (!search_process_tree) {
        /* We strictly require the parent process to be the originating process. */
        if (parent_pid == onefile_parent_pid) {
            succeeded = true; /* OK */
            goto end;
        } else {
            PYI_ERROR("Security validation failure: invalid originating onefile parent process (different PID)!\n");
            goto end;
        }
    }

    /* We strictly require grandparent or one of further ancestor processes
     * to be the originating process. So a match on immediate parent is
     * considered a failure here. */
    if (parent_pid == onefile_parent_pid) {
        PYI_ERROR("Security validation failure: invalid originating onefile parent process (different PID)!\n");
        goto end;
    }

    /* Walk the process tree */
    if (pyi_process_lineage_tracker_add_ancestor(&tracker, parent_pid) < 0) {
        goto end;
    }
    current_pid = parent_pid;

    while (1) {
        PYI_DEBUG("SECURITY: looking up parent of %u...\n", current_pid);

        /* Look up parent PID of the given current PID. */
        if (pyi_process_lineage_tracker_get_parent_pid(&tracker, current_pid, &parent_pid) < 0) {
            goto end;
        }

        /* 0 is used to denote that parent of current-level PID could not
         * be found */
        if (parent_pid == 0) {
            PYI_DEBUG("SECURITY: parent process of %u not found!\n", current_pid);
            break;
        }

        /* Windows implementation of pyi_process_lineage_tracker_get_parent_pid()
         * emits its own message (that also includes process name) */
#if !defined(_WIN32)
        PYI_DEBUG("SECURITY: parent of %u is %u\n", current_pid, parent_pid);
#endif

        /* Check if we reached the end of the process tree. */
        if (parent_pid <= tracker.lowest_valid_pid || parent_pid == current_pid) {
            PYI_DEBUG("SECURITY: reached root of process tree!\n");
            break;
        }

        /* Check if we have a match. */
        if (parent_pid == onefile_parent_pid) {
            PYI_DEBUG("SECURITY: process %u is a valid ancestor process!\n", onefile_parent_pid);
            succeeded = true; /* OK */
            goto end;
        }

        /* Ensure we are not looping, by checking obtained the parent PID
         * against the list of already-seen ancestor PIDs. This might happen
         * if an ancestor process died and had its PID reused. In the context
         * of security validation here, this means that we reached the end of
         * searchable process tree without finding the onefile parent process ID. */
        if (pyi_process_lineage_tracker_check_ancestor_seen(&tracker, parent_pid) != false) {
            PYI_DEBUG("SECURITY: detected parent-process ID loop!\n");
            break;
        }

        /* Add to the list of seen ancestor processes, and ensure we
         * have not hit the maximum allowed depth of process tree. */
        if (pyi_process_lineage_tracker_add_ancestor(&tracker, parent_pid) < 0) {
            goto end;
        }

        current_pid = parent_pid;
    }

    /* We could not find the target PID in the ancestor tree */
    PYI_ERROR("Security validation failure: invalid originating onefile parent process (PID not found)!\n");

end:
    pyi_process_lineage_tracker_cleanup(&tracker);
    return succeeded;
}


/**********************************************************************\
 *              Verification of parent-process executable             *
\**********************************************************************/
/* Verify that the originating onefile parent process uses the same
 * executable as the current process. */
#if defined(_WIN32)

static bool
_pyi_security_verify_onefile_parent_executable_win32(const struct PYI_CONTEXT *pyi_ctx, const DWORD process_id)
{
    HANDLE process_handle;
    wchar_t parent_executable_w[PYI_PATH_MAX];
    wchar_t current_executable_w[PYI_PATH_MAX];
    DWORD buffer_length;

    /* Query the target process for its executable name.
     * QueryFullProcessImageNameW() seems to return a fully-resolved
     * path to the executable, even when the parent process is launched
     * via symbolic link. */
    process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, process_id);
    if (process_handle == INVALID_HANDLE_VALUE) {
        PYI_ERROR_W(L"Security validation failure: failed to obtain information about originating onefile parent process!\n");
        return false;
    }

    buffer_length = PYI_PATH_MAX;
    if (!QueryFullProcessImageNameW(process_handle, PROCESS_NAME_NATIVE, parent_executable_w, &buffer_length)) {
        PYI_ERROR_W(L"Security validation failure: failed to obtain executable path for originating onefile parent process!\n");
        CloseHandle(process_handle);
        return false;
    }

    CloseHandle(process_handle);

    PYI_DEBUG_W(L"SECURITY: originating onefile parent process executable: %ls\n", parent_executable_w);

    /* Look up the current-process executable. We cannot use pyi_ctx->executable_filename,
     * which is resolved using GetModuleFileNameW() for compatibility reasons (see #9510),
     * whereas we need to resolve the executable using QueryFullProcessImageNameW() here
     * to ensure same behavior (i.e., full resolution of file symbolic links, directory
     * symbolic links, and junctions) as above with parent-process executable (see #9508). */
    process_handle = GetCurrentProcess();

    buffer_length = PYI_PATH_MAX;
    if (!QueryFullProcessImageNameW(process_handle, PROCESS_NAME_NATIVE, current_executable_w, &buffer_length)) {
        PYI_ERROR_W(L"Security validation failure: failed to obtain executable path for current process!\n");
        CloseHandle(process_handle);
        return false;
    }

    CloseHandle(process_handle);

    PYI_DEBUG_W(L"SECURITY: current process executable: %ls\n", current_executable_w);

    /* Ensure that same executable is used */
    if (wcscmp(parent_executable_w, current_executable_w) != 0) {
        PYI_ERROR_W(L"Security validation failure: invalid originating onefile parent process (different executable)!\n");
        return false;
    }

    return true;
}

#elif defined(__APPLE__)

static int
_pyi_security_verify_onefile_parent_executable_macos(const struct PYI_CONTEXT *pyi_ctx, const pid_t process_id)
{
    char parent_executable[PYI_PATH_MAX];

    /* proc_pidpath() seems to return a fully-resolved path to the
     * executable, even when the parent process is launched via symbolic
     * link. */
    proc_pidpath(process_id, parent_executable, sizeof(parent_executable));

    PYI_DEBUG("SECURITY: originating onefile parent process executable: %s\n", parent_executable);

    /* Ensure that same executable is used */
    if (strcmp(parent_executable, pyi_ctx->executable_filename) != 0) {
        PYI_ERROR("Security validation failure: invalid originating onefile parent process (different executable)!\n");
        return false;
    }

    return true;
}

#else

static int
_pyi_security_verify_onefile_parent_executable_posix(const struct PYI_CONTEXT *pyi_ctx, const pid_t process_id)
{
    char proc_path[PYI_PATH_MAX];
    char parent_executable[PYI_PATH_MAX];

#if defined(__linux__) || defined(__CYGWIN__) || defined(__NetBSD__)
    const char *proc_path_fmt = "/proc/%d/exe";
#elif defined(__FreeBSD__)
    const char *proc_path_fmt = "/proc/%d/file";
#elif defined(__sun)
    const char *proc_path_fmt = "/proc/%d/path/a.out";
#else
    const char *proc_path_fmt = NULL;
#endif

    /* Raise an error on unsupported POSIX platforms, where we have no
     * way to look up the executable for a given process. */
    if (!proc_path_fmt) {
        PYI_ERROR("Security validation failure: parent-process executable validation is not supported on this platform!\n");
        return false;
    }

    /* Try to look up the /proc entry. On some platforms, the entry points
     * at "true" file location, i.e., canonical and with all symbolic links
     * resolved; on others (e.g., NetBSD), the entry is neither canonical
     * nor fully resolved. So to be safe, always pass the symlink to realpath()
     * for full resolution. This matches the behavior of _pyi_resolve_executable_posix()
     * in pyi_main.c */
    if (snprintf(proc_path, PYI_PATH_MAX, proc_path_fmt, process_id) >= PYI_PATH_MAX) {
        PYI_ERROR("Security validation failure: could not format /proc entry path!\n");
        return false;
    }

    if (realpath(proc_path, parent_executable) == NULL) {
        /* The access to /proc entry might be blocked due to security policy,
         * or by proc filesystem not being mounted (as is the case on FreeBSD
         * by default).  */
        PYI_ERROR("Security validation failure: could not access /proc entry to determine the executable path for originating onefile parent process!\n");
        return false;
    }

    /* Exclude the .exe suffix from the resolved executable path, in order to
     * match the behavior of _pyi_resolve_executable_cygwin() in pyi_main.c */
#if defined(__CYGWIN__)
    if (1) {
        size_t len = strlen(parent_executable);
        if (len >= 5) {
            char *suffix_ptr = parent_executable + len - 4;
            if (strcasecmp(suffix_ptr, ".exe") == 0) {
                PYI_DEBUG("SECURITY: removing .exe suffix from originating onefile parent executable\n");
                *suffix_ptr = 0;
            }
        }
    }
#endif

    PYI_DEBUG("SECURITY: originating onefile parent process executable: %s\n", parent_executable);

    /* Ensure that same executable is used */
    if (strcmp(parent_executable, pyi_ctx->executable_filename) != 0) {
        PYI_ERROR("Security validation failure: invalid originating onefile parent process (different executable)!\n");
        return false;
    }

    return true;
}

#endif

bool
pyi_security_verify_onefile_parent_executable(const struct PYI_CONTEXT *pyi_ctx, const unsigned int onefile_parent_pid)
{
    PYI_DEBUG("SECURITY: verifying executable of originating onefile parent process (%d)...\n", onefile_parent_pid);

    /* Use corresponding platform-specific implementation */
#if defined(_WIN32)
    return _pyi_security_verify_onefile_parent_executable_win32(pyi_ctx, onefile_parent_pid);
#elif defined(__APPLE__)
    return _pyi_security_verify_onefile_parent_executable_macos(pyi_ctx, onefile_parent_pid);
#else
    return _pyi_security_verify_onefile_parent_executable_posix(pyi_ctx, onefile_parent_pid);
#endif
}


/**********************************************************************\
 *            Verification of application's home directory            *
\**********************************************************************/
/* Verify the name of application's top-level / home directory in
 * onefile mode. Check that the directory's name matches the format used
 * by PyInstaller's bootloader, and extract the process ID (PID) of the
 * originating onefile parent process (i.e., the process that set up the
 * directory).
 *
 * The name check should largely prevent spoofed environment variables
 * from being used to pass an arbitrary directory as the top-level
 * application to a onefile child process. However, this could still
 * happen with directories that do conform to PyInstaller's naming scheme;
 * to prevent this, the extracted PID of the originating onefile process
 * needs to be further verified (i.e., that is a parent or an ancestor
 * process of the current process, and that the said process uses same
 * executable as the current process). */
bool
pyi_security_verify_application_home_dir_name(const struct PYI_CONTEXT *pyi_ctx, unsigned int *onefile_parent_pid)
{
    char basename[PYI_PATH_MAX];
    size_t name_len;

    if (!pyi_path_basename(basename, pyi_ctx->application_home_dir)) {
        PYI_ERROR("Security validation failure: failed to obtain name of application's home directory!\n");
        return false;
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
        return false;
    }
#else
    if (name_len != 18) {
        PYI_ERROR("Security validation failure: unexpected name of application's home directory!\n");
        return false;
    }
#endif

    /* Verify the prefix and extract PID part at the same time. Keep in
     * sync with pyi_create_temporary_application_directory() implementations
     * in pyi_utils_posix.c and pyi_utis_win32.c */
    if (sscanf(basename, "_MEI%08x", onefile_parent_pid) != 1) {
        PYI_ERROR("Security validation failure: unexpected name of application's home directory!\n");
        return false;
    }

    return true;
}


/* Verification of owner ID and permissions on top-level application
 * directory for POSIX executables with setuid bit set:
 *  - the owner ID of the top-level application directory must match the
 *    effective user ID
 *  - permissions on the top-level application directory must be set to
 *    0700
 * Applicable to both onefile and onedir builds. No-op on Windows, and
 * no-op on other platforms when setuid bit is not set on the executable. */
bool
pyi_security_verify_application_home_dir_permissions(const struct PYI_CONTEXT *pyi_ctx)
{
#if defined(_WIN32)
    (void)pyi_ctx;
    return true;
#else
    uid_t euid;
    uid_t permissions;
    struct stat application_home_dir_stat;

    /* Applicable only to executables with setuid bit set. */
    if (!pyi_ctx->has_setuid) {
        PYI_DEBUG("SECURITY: setuid bit is not set - skipping verification of owner/permissions of application's home directory.\n");
        return true;
    }

    PYI_DEBUG("SECURITY: setuid bit is set - verifying owner/permissions of application's home directory...\n");

    if (stat(pyi_ctx->application_home_dir, &application_home_dir_stat) < 0) {
        PYI_ERROR("Security validation failure: could not stat() the application's home directory!\n");
        return false;
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
        return false;
    }

    /* Ensure that the application's home directory has permissions used
     * by bootloader when creating ephemeral application directory
     * (i.e., S_IRWXU = 0700). In case of onedir application, it ensures
     * that the contents directory cannot be modified by unprivileged
     * user. */
    permissions = application_home_dir_stat.st_mode & (S_IRWXU | S_IRWXG | S_IRWXO);
    if (permissions != S_IRWXU) {
        PYI_ERROR("Security validation failure: application's home directory has invalid permissions (0%o)!\n", permissions);
        return false;
    }

    return true;
#endif
}
