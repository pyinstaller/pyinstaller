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
 * to POSIX platforms.
 */

/* Having a header included outside of the ifdef block prevents the compilation
 * unit from becoming empty, which is disallowed by pedantic ISO C. */
#include "pyi_global.h"

#ifndef _WIN32

#include <stdio.h>  /* FILE */
#include <stdlib.h>
#include <stddef.h> /* ptrdiff_t */
#include <unistd.h> /* rmdir, unlink, mkdtemp */
#include <string.h>
#include <errno.h>
#include <signal.h> /* kill */
#include <sys/stat.h> /* struct stat */
#include <sys/wait.h>

#if defined(PYI_USE_POSIX_SEMAPHORE)
    #include <sys/mman.h> /* mmap */
    #include <semaphore.h> /* POSIX semaphore API */
    /* Use MAP_ANON as synonym for MAP_ANONYMOUS if the latter is unavailable. */
    #ifndef MAP_ANONYMOUS
        #ifdef MAP_ANON
            #define MAP_ANONYMOUS MAP_ANON
        #else
            #error "Neither MAP_ANONYMOUS nor MAP_ANON is defined."
        #endif
    #endif
#elif defined(PYI_USE_SYSV_SEMAPHORE)
    #include <sys/sem.h> /* SysV semaphore API */
#endif

#include <dirent.h>

#ifndef SIGCLD
    #define SIGCLD SIGCHLD /* not defined on macOS */
#endif

#ifndef sighandler_t
    typedef void (*sighandler_t)(int);
#endif

/* PyInstaller headers. */
#include "pyi_utils.h"
#include "pyi_path.h"
#include "pyi_main.h"
#include "pyi_apple_events.h"


/**********************************************************************\
 *                  Environment variable management                   *
\**********************************************************************/
char *
pyi_getenv(const char *variable)
{
    char *value;

    /* Use standard POSIX getenv(). */
    value = getenv(variable);

    /* On some POSIX platforms, `unsetenv` is not available. In such
     * cases, we "undefine" environment variables by setting them to
     * empty strings. Therefore, treat empty environment variables as
     * being undefined. */
    return (value && value[0]) ? strdup(value) : NULL; /* Return a copy */
}

int
pyi_setenv(const char *variable, const char *value)
{
    /* Standard POSIX function. */
    return setenv(variable, value, 1 /* overwrite */);
}

int
pyi_unsetenv(const char *variable)
{
#if HAVE_UNSETENV
    return unsetenv(variable);
#else /* HAVE_UNSETENV */
    /* If `unsetenv` is unavailable, set the variable to an empty string. */
    return setenv(variable, "", 1 /* overwrite */);
#endif /* HAVE_UNSETENV */
}


/**********************************************************************\
 *         Temporary application top-level directory (onefile)        *
\**********************************************************************/
/*
 * Function 'mkdtemp' (make temporary directory) is missing on some POSIX platforms:
 * - On Solaris function 'mkdtemp' is missing.
 * - On AIX 5.2 function 'mkdtemp' is missing. It is there in version 6.1 but we don't know
 *   the runtime platform at compile time, so we always include our own implementation on AIX.
 */
#if !defined(HAVE_MKDTEMP)

static char *
mkdtemp(char *template)
{
    if (!mktemp(template) ) {
        return NULL;
    }

    if (mkdir(template, 0700) ) {
        return NULL;
    }

    return template;
}

#endif /* !defined(HAVE_MKDTEMP) */

/* Resolve the temporary directory specified by user via runtime_tmpdir
 * option, and create corresponding directory tree. */
static char *
_pyi_create_runtime_tmpdir(const char *runtime_tmpdir)
{
    char directory_tree_path[PYI_PATH_MAX];
    char *subpath_cursor;

    /* Ensure runtime_tmpdir (and thus also its sub-path components)
     * do not exceed path limit. */
    if (strlen(runtime_tmpdir) >= PYI_PATH_MAX) {
        PYI_WARNING("LOADER: length of runtime-tmpdir exceeds maximum path length!\n");
        return NULL;
    }

    /* Recursively create the directory structure
     *
     * NOTE: we call mkdir with mode 0777 for this part of directory
     * tree, as it might be shared by application instances ran by
     * different users. Only the last component (the actual _MEIXXXXXX
     * directory), created by the caller, uses 0700 to restrict access
     * to current user.
     *
     * NOTE2: we ignore errors returned by mkdir; if we actually fail to
     * create (a part of) directory tree here, we will catch the error
     * when we try to resolve the full path to it later on. */
    for(subpath_cursor = strchr(runtime_tmpdir, '/'); subpath_cursor != NULL; subpath_cursor = strchr(++subpath_cursor, '/')) {
        int subpath_length = subpath_cursor - runtime_tmpdir;

        /* Initial / in absolute path */
        if (subpath_length == 0) {
            continue;
        }

        snprintf(directory_tree_path, PYI_PATH_MAX, "%.*s", subpath_length, runtime_tmpdir);
        PYI_DEBUG("LOADER: creating runtime-tmpdir path component: %s\n", directory_tree_path);
        mkdir(directory_tree_path, 0777);
    }

    /* Create full path; necessary if runtime_tmpdir did not end with
     * path separator. */
    PYI_DEBUG("LOADER: creating runtime-tmpdir path: %s\n", runtime_tmpdir);
    mkdir(runtime_tmpdir, 0777);

    /* Now that directory exists, try to resolve full path to it. */
    return realpath(runtime_tmpdir, NULL); /* Let realpath allocate the buffer */
}


/* Append the _MEIXXXXXX string to the temporary directory path template,
 * and try creating the temporary directory. */
static int
_pyi_format_and_create_tmpdir(char *tmpdir_path)
{
    size_t path_len;
    unsigned char needs_separator;

    /* Compute length of the given temporary directory path - to ensure
     * that strcat operations below do not exceed buffer length. */
    path_len = strlen(tmpdir_path);

    /* Check whether the given path ends with separator or not. Typically,
     * it should not, but on macOS, the value from $TMPDIR does. */
    needs_separator = tmpdir_path[path_len - 1] != PYI_SEP;

    /* Add separator , _MEI, and six X characters required by mkdtemp */
    path_len += needs_separator + 4 + 6;
    if (path_len >= PYI_PATH_MAX) {
        return -1;
    }

    if (needs_separator) {
        strcat(tmpdir_path, PYI_SEPSTR);
    }
    strcat(tmpdir_path, "_MEIXXXXXX");

    /* Try creating the directory */
    if (mkdtemp(tmpdir_path) == NULL) {
        return -1;
    }

    return 0;
}

int
pyi_create_temporary_application_directory(struct PYI_CONTEXT *pyi_ctx)
{
    static const char *candidate_env_vars[] = {
        "TMPDIR",
        "TEMP",
        "TMP"
    };

    static const char *candidate_tmp_dirs[] = {
        "/tmp",
        "/var/tmp",
        "/usr/tmp"
    };

    int i;

    /* If specified, use runtime_tmpdir */
    if (pyi_ctx->runtime_tmpdir != NULL) {
        char *resolved_runtime_tmpdir;
        int ret;

        /* Ensure runtime_tmpdir exists, and resolve full path to it */
        resolved_runtime_tmpdir = _pyi_create_runtime_tmpdir(pyi_ctx->runtime_tmpdir);
        if (resolved_runtime_tmpdir == NULL) {
            PYI_WARNING("Failed to create or resolve runtime_tmpdir from given path: %s\n", pyi_ctx->runtime_tmpdir);
            return -1;
        }

        ret = snprintf(pyi_ctx->application_home_dir, PYI_PATH_MAX, "%s", resolved_runtime_tmpdir);
        free(resolved_runtime_tmpdir);
        if (ret >= PYI_PATH_MAX) {
            PYI_WARNING("Length of resolved runtime_tmpdir exceeds maximum path length!\n");
            return -1;
        }

        /* Try to create _MEIXXXXXX directory under the runtime_tmpdir */
        return _pyi_format_and_create_tmpdir(pyi_ctx->application_home_dir);
    }

    /* Check the standard environment variables */
    for (i = 0; i < sizeof(candidate_env_vars)/sizeof(candidate_env_vars[0]); i++) {
        char *env_var_value = pyi_getenv(candidate_env_vars[i]);
        int ret;

        if (env_var_value == NULL) {
            continue;
        }

        ret = snprintf(pyi_ctx->application_home_dir, PYI_PATH_MAX, "%s", env_var_value);
        free(env_var_value);

        if (ret >= PYI_PATH_MAX) {
            continue;
        }

        if (_pyi_format_and_create_tmpdir(pyi_ctx->application_home_dir) == 0) {
            return 0;
        }
    }

    /* Check the standard temporary directory paths */
    for (i = 0; i < sizeof(candidate_tmp_dirs)/sizeof(candidate_tmp_dirs[0]); i++) {
         snprintf(pyi_ctx->application_home_dir, PYI_PATH_MAX, "%s", candidate_tmp_dirs[i]);
         if (_pyi_format_and_create_tmpdir(pyi_ctx->application_home_dir) == 0) {
            return 0;
        }
    }

    return -1; /* No suitable location found */
}


/**********************************************************************\
 *                  Recursive removal of a directory                  *
\**********************************************************************/
int
pyi_recursive_rmdir(const char *dir_path)
{
    DIR *dir_handle;
    struct dirent *dir_entry;
    struct stat stat_buf;
    int dir_path_length;
    int buffer_size;
    char entry_path[PYI_PATH_MAX];

    /* Make a copy of directory path (and append a path separator), into
     * mutable buffer that we will use to construct entries' full paths.
     * Store the length of the directory path string; this allows us to
     * overwrite only the sub-component part of the string, without having
     * to copy the directory path each time. */
    dir_path_length = snprintf(entry_path, PYI_PATH_MAX, "%s%c", dir_path, PYI_SEP);
    if (dir_path_length >= PYI_PATH_MAX) {
        return -1;
    }
    buffer_size = PYI_PATH_MAX - dir_path_length; /* Remaining buffer size */

    /* Open the directory */
    dir_handle = opendir(dir_path);
    if (dir_handle == NULL) {
        return -1;
    }

    /* Iterate over directory contents */
    for (dir_entry = readdir(dir_handle); dir_entry != NULL; dir_entry = readdir(dir_handle))
    {
        /* Skip . and .. */
        if (strcmp(dir_entry->d_name, ".") == 0 || strcmp(dir_entry->d_name, "..") == 0) {
            continue;
        }

        /* Construct the full path, by overwriting the part of string
         * that starts after path directory and separator. */
        if (snprintf(entry_path + dir_path_length, buffer_size, "%s", dir_entry->d_name) >= buffer_size) {
            continue;
        }

        /* Deteremine the type of entry, and remove it. Use lstat()
         * instead of stat() in order to prevent recursion into symlinked
         * directories. On errors, emit debug messages to simplify
         * debugging, and keep going on. We want to remove everything we
         * can; if we fail to remove an entry here, we will also fail
         * to remove the top-level directory, and will return error
         * there and then. */
        if (lstat(entry_path, &stat_buf) == 0) {
            if (S_ISDIR(stat_buf.st_mode) ) {
                /* Recurse into sub-directory */
                if (pyi_recursive_rmdir(entry_path) < 0) {
                    PYI_DEBUG("LOADER: failed to remove directory: %s\n", entry_path);
                }
            } else {
                if (unlink(entry_path) < 0) {
                    PYI_DEBUG("LOADER: failed to remove file: %s\n", entry_path);
                }
            }
        }
    }
    closedir(dir_handle);

    /* Finally, remove the directory; the return value of rmdir (0 on
     * success, -1 on error) maps directly to this function's return. */
    return rmdir(dir_path);
}


/**********************************************************************\
 *                  Child process spawning (onefile)                  *
\**********************************************************************/
#if !defined(__APPLE__)

int
pyi_utils_set_library_search_path(const char *path)
{
    /* On AIX, LIBPATH is used to set dynamic library search path. On
     * other POSIX platforms (other than macOS), LD_LIBRARY_PATH is used. */
#ifdef AIX
    const char *variable_name = "LIBPATH";
    const char *variable_name_copy = "LIBPATH_ORIG";
#else
    const char *variable_name = "LD_LIBRARY_PATH";
    const char *variable_name_copy = "LD_LIBRARY_PATH_ORIG";
#endif

    char *orig_library_path = NULL;

    int rc = 0;

    /* Try retrieving the original value of the library-path environment
     * variable. */
    orig_library_path = pyi_getenv(variable_name);
    if (orig_library_path) {
        char *new_library_path;
        int new_library_path_length;

        /* Variable is set; store a copy (*_ORIG environment variable),
         * so that it can be restored, if necessary. */
        PYI_DEBUG("LOADER: setting %s=%s\n", variable_name_copy, orig_library_path);
        pyi_setenv(variable_name_copy, orig_library_path);

        /* Compute the length of the new environment variable value:
         * given path + separator + original value + terminating NULL. */
        new_library_path_length = strlen(orig_library_path) + strlen(path) + 2;
        new_library_path = malloc(new_library_path_length);
        if (new_library_path == NULL) {
            rc = -1; /* Allocation failed */
        } else {
            snprintf(new_library_path, new_library_path_length, "%s:%s", path, orig_library_path);
            PYI_DEBUG("LOADER: setting %s=%s\n", variable_name, new_library_path);
            rc = pyi_setenv(variable_name, new_library_path);
            free(new_library_path);
        }

        free(orig_library_path);
    } else {
        /* Variable not set; the new search path should contain just the
         * given path. */
        PYI_DEBUG("LOADER: setting %s=%s\n", variable_name, path);
        rc = pyi_setenv(variable_name, path);
    }

    return rc;
}

#endif /* !defined(__APPLE__) */

/*
 * If the program is activated by a systemd socket, systemd will set
 * LISTEN_PID, LISTEN_FDS environment variable for that process.
 *
 * LISTEN_PID is set to the pid of the parent process of bootloader,
 * which is forked by systemd.
 *
 * Bootloader will duplicate LISTEN_FDS to child process, but the
 * LISTEN_PID environment variable remains unchanged.
 *
 * Here we change the LISTEN_PID to the child pid in child process.
 * So the application can detect it and use the LISTEN_FDS created
 * by systemd.
 */
static int
_pyi_set_systemd_env()
{
    const char *env_var_name = "LISTEN_PID";
    char *value;

    value = pyi_getenv(env_var_name);
    if (value != NULL) {
        /* 32 characters should be enough to accommodate the largest
         * value unsigned 64-bit integer (2^64 - 1), which takes up 20
         * characters. Even on contemporary 64-bit linux systems, PID
         * values have theoretical limit of 2^22, so there is a lot of
         * headroom here...   */
        char pid_str[32];

        free(value); /* Free the copy of original value, which we do not need. */

        snprintf(pid_str, 32, "%ld", (unsigned long)getpid());
        return pyi_setenv(env_var_name, pid_str);
    }

    return 0;
}

static void
_ignoring_signal_handler(int signum)
{
    /* Ignore the signal. Avoid generating debug messages as per
     * explanation in _signal_handler(). */
    (void)signum; /* Supress unused argument warnings */
}

static void
_signal_handler(int signum)
{
    int original_errno = errno; /* Store original errno */
    pid_t child_pid = global_pyi_ctx->child_pid; /* Read from volatile global variable */

    /* Forward signal to the child. Avoid generating debug messages, as
     * functions involved are generally not signal safe. Furthermore, it
     * may result in endless spamming of SIGPIPE, as reported and
     * diagnosed in #5270. */

#if defined(LAUNCH_DEBUG)
    global_pyi_ctx->signal_forward_all++;
#endif

    if (child_pid <= 0) {
        /* No-op if child process does not exist (yet or anymore), or
         * if fork() returned -1 due to error. */
#if defined(LAUNCH_DEBUG)
        global_pyi_ctx->signal_forward_noop++;
#endif
        return;
    }

#if defined(LAUNCH_DEBUG)
    if (kill(child_pid, signum) == 0) {
        global_pyi_ctx->signal_forward_ok++;
    } else {
        global_pyi_ctx->signal_forward_error++;
    }
#else
    kill(child_pid, signum);
#endif

    errno = original_errno; /* Restore original errno */
}

/* Start frozen application in a subprocess. The frozen application runs
 * in a subprocess. */
int
pyi_utils_create_child(struct PYI_CONTEXT *pyi_ctx)
{
    pid_t child_pid = 0;
    int rc = 0;
    int wait_rc = -1;

    /* As indicated in signal(7), signal numbers range from 1-31 (standard)
     * and 32-64 (Linux real-time). */
    const size_t num_signals = 65;

    sighandler_t signal_handler;
    int signum;

    /* Create semaphore for synchronizing child and parent; we need to
     * ensure that the child starts executing user's python code only
     * *after* the parent has fully completed the `fork()` call *and* stored
     * the child process ID to `pyi_ctx->child_pid` for the forwarding
     * signal handlers (as well as installed the said handlers).
     * Failing to do so leads to sporadic failures in our signal handling
     * test (`test_onefile_signal_handling`) when performed under heavy
     * CPU load.
     *
     * Our first choice of API are unnamed POSIX semaphores, which should
     * be available on most POSIX platforms. However, they are unavailable
     * on macOS (i.e., only stubs are implemented), so we also need to support
     * the old SysV semaphore API... */

#if defined(PYI_USE_POSIX_SEMAPHORE)
    sem_t *sem_ptr;

    /* Create anonymous shared memory region for the semaphore. */
    PYI_DEBUG("LOADER: creating sync semaphore...\n");
    sem_ptr = mmap(NULL, sizeof(sem_t), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (sem_ptr == MAP_FAILED) {
        PYI_DEBUG("LOADER: failed to create shared memory region for sync semaphore (errno %d) - disabling sync.\n", errno);
    } else {
        /* Initialize semaphore with pshared=1 and value=0 (locked/acquired). */
        if (sem_init(sem_ptr, 1, 0) < 0) {
            PYI_DEBUG("LOADER: failed to initialize sync semaphore (errno %d) - disabling sync.\n", errno);
            /* Unmap shared memory, and reset pointer to it for later checks. */
            munmap(sem_ptr, sizeof(sem_t));
            sem_ptr = MAP_FAILED;
        }
    }
#elif defined(PYI_USE_SYSV_SEMAPHORE)
    /* Argument for semctl(); according to API, we need to provide our
     * own union definition... */
    union {
        int val;
        struct semid_ds *buf;
        unsigned short *array;
    } sem_arg;

    struct sembuf sem_op;  /* Argument for semop() */
    int sem_id = -1;  /* Semaphore (array) ID */

    /* Create semaphore */
    PYI_DEBUG("LOADER: creating sync semaphore...\n");
    sem_id = semget(IPC_PRIVATE, 1, 0660 | IPC_CREAT | IPC_EXCL);
    if (sem_id < 0) {
        /* Allow semaphore creation to fail, for whatever reason, and
         * disable parent/child sync in that case. Not having the sync
         * should be of little consequence outside of PyInstaller's own
         * POSIX signal test suite, so it should not be considered fatal.
         * For example, under cygwin, semget() is only available when
         * cygserver is running, which might not always be the case.
         * There might be other failure modes on other POSIX systems. */
        PYI_DEBUG("LOADER: failed to create sync semaphore (errno %d) - disabling sync.\n", errno);
    }

    /* Initialize semaphore's value to 0 (= locked/acquired) */
    if (sem_id >= 0) {
        sem_arg.val = 0;
        if (semctl(sem_id, 0, SETVAL, sem_arg) < 0) {
            PYI_PERROR("semctl", "Failed to initialize sync semaphore!\n");
            goto cleanup;
        }
    }
#endif /* defined(PYI_USE_SYSV_SEMAPHORE) */

    /* macOS: Apple Events handling */
#if defined(__APPLE__) && defined(WINDOWED)
    /* Initialize pyi_argc and pyi_argv with original argc and argv.
     * Do this regardless of argv-emulation setting, because
     * pyi_utils_initialize_args() also filters out -psn_xxx argument. */
    if (pyi_utils_initialize_args(pyi_ctx, pyi_ctx->argc, pyi_ctx->argv) < 0) {
        goto cleanup;
    }

    /* Install Apple Event handlers */
    pyi_ctx->ae_ctx = pyi_apple_install_event_handlers(pyi_ctx);
    if (pyi_ctx->ae_ctx == NULL) {
        goto cleanup;
    }

    /* argv emulation; do a short (250 ms) cycle of Apple Events processing
     * before bringing up the child process */
    if (pyi_ctx->macos_argv_emulation) {
        pyi_apple_process_events(pyi_ctx->ae_ctx, 0.25);  /* short timeout (250 ms) */
    }
#endif

    /* Fork the child process. */
    child_pid = fork();
    if (child_pid < 0) {
        PYI_WARNING("LOADER: failed to fork child process: %s\n", strerror(errno));
        goto cleanup;
    }

    /* Child code. */
    if (child_pid == 0) {
        /* Replace process by starting a new application. */
        /* If modified arguments (pyi_ctx->pyi_argv) are available, use
         * those. Otherwise, use the original pyi_ctx->argv. */
        char *const *argv = (pyi_ctx->pyi_argv != NULL) ? pyi_ctx->pyi_argv : pyi_ctx->argv;
        const int argc = (pyi_ctx->pyi_argv != NULL) ? pyi_ctx->pyi_argc : pyi_ctx->argc;

        /* Wait on the sync semaphore */
#if defined(PYI_USE_POSIX_SEMAPHORE)
        if (sem_ptr != MAP_FAILED) {
            PYI_DEBUG("LOADER: waiting on sync semaphore...\n");
            if (sem_wait(sem_ptr) < 0) {
                PYI_PERROR("sem_wait", "Failed to wait on sync semaphore!\n");
            }
        }
#elif defined(PYI_USE_SYSV_SEMAPHORE)
        if (sem_id >= 0) {
            PYI_DEBUG("LOADER: waiting on sync semaphore...\n");
            sem_op.sem_num = 0;
            sem_op.sem_op = -1; /* P/decrement (= acquire semaphore) */
            sem_op.sem_flg = 0;
            if (semop(sem_id, &sem_op, 1) < 0) {
                PYI_PERROR("semop", "Failed to wait on sync semaphore!\n");
            }
        }
#endif /* defined(PYI_USE_SYSV_SEMAPHORE) */

        /* Modify the LISTEN_PID environment variable, if necessary */
        if (_pyi_set_systemd_env() != 0) {
            PYI_WARNING("LOADER: application is started by systemd socket, but we cannot set proper LISTEN_PID on it.\n");
        }

        /* NOTE: if execvp() fails for whatever reason, we must immediately
         * exit the (forked) child process using exit() call. Otherwise,
         * the forked child process will continue executing the cleanup
         * codepath, which is intended for the parent process, and will
         * end up interfering with the cleanup in the actual parent
         * process - for example, there will be two attempts at removing
         * the application's temporary directory. */
        if (pyi_ctx->dynamic_loader_filename[0] != 0) {
            char *const *exec_argv;

            PYI_DEBUG("LOADER: starting child process via execvp and dynamic linker/loader: %s\n", pyi_ctx->dynamic_loader_filename);
            exec_argv = pyi_prepend_dynamic_loader_to_argv(argc, argv, pyi_ctx->dynamic_loader_filename);
            if (exec_argv == NULL) {
                PYI_ERROR("LOADER: failed to allocate argv array for execvp!\n");
                exit(-1);
            }
            if (execvp(pyi_ctx->dynamic_loader_filename, exec_argv) < 0) {
                PYI_ERROR("LOADER: failed to start child process: %s\n", strerror(errno));
                exit(-1);
            }
        } else {
            PYI_DEBUG("LOADER: starting child process via execvp\n");
            if (execvp(pyi_ctx->executable_filename, argv) < 0) {
                PYI_ERROR("LOADER: failed start child process: %s\n", strerror(errno));
                exit(-1);
            }
        }

        /* NOTREACHED */
    }

    /* From here to end-of-function is parent code (since the child exec'd,
     * or exited on exec failure). */
    PYI_DEBUG("LOADER: forked child process with PID: %d\n", child_pid);

    /* Store child PID to context structure for use in forwarding signal
     * handler (as well as Apple event handler on macOS). */
    pyi_ctx->child_pid = child_pid;

    /* Install signal handlers to either forward received signals to the
     * child process, or ignore them (effectively blocking them). */
    if (pyi_ctx->ignore_signals) {
        PYI_DEBUG("LOADER: registering signal handlers to ignore received signals.\n");
        signal_handler = &_ignoring_signal_handler;
    } else {
        PYI_DEBUG("LOADER: registering signal handlers to forward received signals to child.\n");
        signal_handler = &_signal_handler;
    }

    for (signum = 0; signum < num_signals; ++signum) {
        /* Don't mess with SIGCHLD/SIGCLD; it affects our ability
         * to wait() for the child to exit. Similarly, do not change
         * don't change SIGTSP handling to allow Ctrl-Z */
        if (signum == SIGCHLD || signum == SIGCLD || signum == SIGTSTP) {
            continue;
        }
        signal(signum, signal_handler);
    }

    /* Signal the sync semaphore */
#if defined(PYI_USE_POSIX_SEMAPHORE)
    if (sem_ptr != MAP_FAILED) {
        PYI_DEBUG("LOADER: signalling the sync semaphore...\n");
        if (sem_post(sem_ptr) < 0) {
            PYI_PERROR("sem_post", "Failed to signal the sync semaphore!\n");
        }
    }
#elif defined(PYI_USE_SYSV_SEMAPHORE)
    if (sem_id >= 0) {
        PYI_DEBUG("LOADER: signalling the sync semaphore...\n");
        sem_op.sem_num = 0;
        sem_op.sem_op = 1; /* V/increment (= release semaphore) */
        sem_op.sem_flg = 0;
        if (semop(sem_id, &sem_op, 1) < 0) {
            PYI_PERROR("semop", "Failed to signal the sync semaphore!\n");
        }
    }
#endif /* defined(PYI_USE_SYSV_SEMAPHORE) */

#if defined(__APPLE__) && defined(WINDOWED)
    /* macOS: forward events to child */
    do {
        /* The below loop will iterate about once every second on Apple,
         * waiting on the event queue most of that time. */
        wait_rc = waitpid(child_pid, &rc, WNOHANG);
        if (wait_rc == 0) {
            /* Check if we have a pending event that we need to forward... */
            if (pyi_apple_has_pending_event(pyi_ctx->ae_ctx)) {
                /* Attempt to re-send the pending event after 0.5 second delay. */
                if (pyi_apple_send_pending_event(pyi_ctx->ae_ctx, 0.5) != 0) {
                    /* Do not process additional events until the pending one
                     * is successfully forwarded (or cleaned up by error). */
                    continue;
                }
            }
            /* Wait for and process AppleEvents with a 1-second timeout, forwarding
             * events to the child. */
            pyi_apple_process_events(pyi_ctx->ae_ctx, 1.0);  /* long timeout (1 sec) */
        }
    } while (!wait_rc);

    /* Check if we have a pending event to forward (for diagnostics) */
    if (pyi_apple_has_pending_event(pyi_ctx->ae_ctx)) {
        PYI_DEBUG("LOADER [AppleEvent]: child terminated before pending event could be forwarded!\n");
        pyi_apple_cleanup_pending_event(pyi_ctx->ae_ctx);
    }

    /* Uninstall event handlers */
    pyi_apple_uninstall_event_handlers(&pyi_ctx->ae_ctx);
#else
    wait_rc = waitpid(child_pid, &rc, 0);
#endif

    /* Reset stored child PID - this aims to immediately turn forwarding
     * signal handler into no-op (due to `pyi_ctx->child_pid != 0` check). */
     pyi_ctx->child_pid = 0;

    if (wait_rc < 0) {
        PYI_WARNING("LOADER: failed to wait for child process: %s\n", strerror(errno));
    }

    /* After child process exited, reset signal handlers to default values. */
    PYI_DEBUG("LOADER: restoring signal handlers\n");
    for (signum = 0; signum < num_signals; ++signum) {
        signal(signum, SIG_DFL);
    }

    /* Display statistics from forwarding signal-handler. */
#if defined(LAUNCH_DEBUG)
    if (!pyi_ctx->ignore_signals) {
        PYI_DEBUG(
            "LOADER: signal forwarding statistics: all=%u, ok=%u, err=%u, noop=%u\n",
            pyi_ctx->signal_forward_all,
            pyi_ctx->signal_forward_ok,
            pyi_ctx->signal_forward_error,
            pyi_ctx->signal_forward_noop
        );
    }
#endif

cleanup:
    /* Destroy the sync semaphore (if available) */
#if defined(PYI_USE_POSIX_SEMAPHORE)
    if (sem_ptr != MAP_FAILED) {
        if (sem_destroy(sem_ptr) < 0) {
            PYI_WARNING("LOADER: failed to destroy sync semaphore (errno %d)!\n", errno);
        }
        if (munmap(sem_ptr, sizeof(sem_t)) < 0) {
            PYI_WARNING("LOADER: failed to unmap shared memory of sync semaphore (errno %d)!\n", errno);
        }
    }
#elif defined(PYI_USE_SYSV_SEMAPHORE)
    if (sem_id >= 0) {
        if (semctl(sem_id, 0, IPC_RMID) < 0) {
            PYI_WARNING("LOADER: failed to destroy sync semaphore (errno %d)!\n", errno);
        }
    }
#endif /* defined(PYI_USE_SYSV_SEMAPHORE) */

    /* Clean up the modified copy of command-line arguments (currently
     * applicable only to macOS windowed bootloader builds). */
#if defined(__APPLE__) && defined(WINDOWED)
    pyi_utils_free_args(pyi_ctx);
#endif

    /* Either wait() failed, or we jumped to `cleanup` and
     * didn't wait() at all. Either way, exit with error,
     * because rc does not contain a valid process exit code. */
    if (wait_rc < 0) {
        PYI_DEBUG("LOADER: exiting early\n");
        return 1;
    }

    if (WIFEXITED(rc)) {
        PYI_DEBUG("LOADER: returning child exit status %d\n", WEXITSTATUS(rc));
        return WEXITSTATUS(rc);
    }

    /* Process ended abnormally */
    pyi_ctx->child_signalled = WIFSIGNALED(rc);
    if (pyi_ctx->child_signalled) {
        pyi_ctx->child_signal = WTERMSIG(rc);
        PYI_DEBUG("LOADER: child received signal %d; storing for re-raise after cleanup...\n", pyi_ctx->child_signal);
    }
    return 1;
}


/**********************************************************************\
 *                 Argument filtering and modification                *
\**********************************************************************/
/*
 * Initialize private pyi_argc and pyi_argv from the given argc and
 * argv by creating a deep copy. The resulting pyi_argc and pyi_argv
 * can be retrieved directly from PYI_CONTEXT structure, and are
 * freed/cleaned-up by calling pyi_utils_free_args().
 *
 * The pyi_argv contains pyi_argv + 1 elements, with the last element
 * being NULL (i.e., it is execv-compatible NULL-terminated array).
 *
 * On macOS, this function filters out the -psnxxx argument that is
 * passed to executable when .app bundle is launched from Finder:
 * https://stackoverflow.com/questions/10242115/os-x-strange-psn-command-line-parameter-when-launched-from-finder
 */
int pyi_utils_initialize_args(struct PYI_CONTEXT *pyi_ctx, const int argc, char *const argv[])
{
    int i;

    pyi_ctx->pyi_argc = 0;
    pyi_ctx->pyi_argv = (char**)calloc(argc + 1, sizeof(char*));
    if (!pyi_ctx->pyi_argv) {
        PYI_ERROR("LOADER: failed to allocate pyi_argv: %s\n", strerror(errno));
        return -1;
    }

    for (i = 0; i < argc; i++) {
        char *tmp;

        /* Filter out -psnxxx argument that is used on macOS to pass
         * unique process serial number (PSN) to .app bundles launched
         * via Finder. */
#if defined(__APPLE__) && defined(WINDOWED)
        if (strstr(argv[i], "-psn") == argv[i]) {
            continue;
        }
#endif

        /* Copy the argument */
        tmp = strdup(argv[i]);
        if (!tmp) {
            PYI_ERROR("LOADER: failed to strdup argv[%d]: %s\n", i, strerror(errno));
            /* If we cannot allocate basic amounts of memory at this critical point,
             * we should probably just give up. */
            return -1;
        }
        pyi_ctx->pyi_argv[pyi_ctx->pyi_argc++] = tmp;
    }

    return 0;
}

/*
 * Append given argument to private pyi_argv and increment pyi_argc.
 * The pyi_argv array is reallocated accordingly.
 *
 * Returns 0 on success, -1 on failure (due to failed array reallocation).
 * On failure, pyi_argv and pyi_argc remain unchanged.
 */
int pyi_utils_append_to_args(struct PYI_CONTEXT *pyi_ctx, const char *arg)
{
    char **new_pyi_argv;
    char *arg_copy;

    /* Make a copy of new argument */
    arg_copy = strdup(arg);
    if (!arg_copy) {
        return -1;
    }

    /* Reallocate pyi_argv array, making space for new argument plus
     * terminating NULL */
    new_pyi_argv = (char**)realloc(pyi_ctx->pyi_argv, (pyi_ctx->pyi_argc + 2) * sizeof(char *));
    if (!new_pyi_argv) {
        free(arg_copy);
        return -1;
    }
    pyi_ctx->pyi_argv = new_pyi_argv;

    /* Store new argument */
    pyi_ctx->pyi_argv[pyi_ctx->pyi_argc++] = arg_copy;
    pyi_ctx->pyi_argv[pyi_ctx->pyi_argc] = NULL;

    return 0;
}

/*
 * Free/clean-up the private arguments (pyi_argv).
 */
void pyi_utils_free_args(struct PYI_CONTEXT *pyi_ctx)
{
    /* Free each entry */
    int i;
    for (i = 0; i < pyi_ctx->pyi_argc; i++) {
        free(pyi_ctx->pyi_argv[i]);
    }

    /* Free the array itself */
    free(pyi_ctx->pyi_argv);

    /* Clean-up the variables, just in case */
    pyi_ctx->pyi_argc = 0;
    pyi_ctx->pyi_argv = NULL;
}


/*
 * Allocate new argv array and prepend the given dynamic linker/loader
 * name to it. Used when restarting or spawning process via execvp().
 *
 * Since execvp() copies the array, we can create a shallow copy of
 * argv here.
 */
char *const *pyi_prepend_dynamic_loader_to_argv(const int argc, char *const argv[], char *const loader_filename)
{
    char **new_argv;
    int i;

    /* Allocate the new array; loader name + elements of argv + terminating NULL */
    new_argv = (char **)calloc(argc + 2, sizeof(char *));
    if (new_argv == NULL) {
        return NULL;
    }

    /* Shallow copy of the elements. */
    new_argv[0] = loader_filename;
    for (i = 0; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }

    return new_argv;
}

#endif /* ifndef _WIN32 */
