// -----------------------------------------------------------------------------
// Copyright (c) 2020-2021, PyInstaller Development Team.
//
// Distributed under the terms of the GNU General Public License (version 2
// or later) with exception for distributing the bootloader.
//
// The full license is in the file COPYING.txt, distributed with this software.
//
// SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
// -----------------------------------------------------------------------------

#include <sys/types.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>

#include "pyi_global.h"
#include <errno.h>

#include <setjmp.h> // required fo cmocka :-(
#include <cmocka.h>

int checkFile(char *buf, const char *fmt, ...);

static void test_checkFile(void **state) {
    char result[PATH_MAX];

    // TODO: use some mocks to determine stat() output

    errno = 0;
    assert_int_equal(-1, checkFile(result, "%s%s%s.pkg", "a1", "bb", "cc", "dd"));
    assert_int_not_equal(errno, 0); // formatting passed, stat failed
    assert_string_equal(result, "a1bbcc.pkg");

    errno = 0;
    assert_int_equal(-1, checkFile(result, "%s", ""));
    assert_int_not_equal(errno, 0); // formatting passed, stat failed
    assert_string_equal(result, "");

    char *path2 = (char *) malloc(PATH_MAX+10);
    memset(path2, 'a', PATH_MAX+8);
    // a few bytes more
    errno = 0;
    path2[PATH_MAX+8] = '\0';
    assert_int_equal(-1, checkFile(result, "%s%s%s.pkg", "a1", path2, "ccc"));
    assert_int_equal(errno, 0); // formatting formatting failed
    // exact length
    errno = 0;
    path2[PATH_MAX] = '\0';
    assert_int_equal(-1, checkFile(result, "%s", path2));
    assert_int_equal(errno, 0); // formatting formatting failed
    // one byte less
    errno = 0;
    path2[PATH_MAX-1] = '\0';
    assert_int_equal(-1, checkFile(result, "%s", path2));
    assert_int_not_equal(errno, 0); // formatting passed, stat failed
}

int splitName(char *path, char *filename, const char *item);

static void test_splitName(void **state) {
    char path[PATH_MAX];
    char filename[PATH_MAX];

    // TODO: use some mocks to determine

    assert_int_equal(0, splitName(path, filename, "aaa:bbb"));
    assert_string_equal(path, "aaa");
    assert_string_equal(filename, "bbb");

    assert_int_equal(-1, splitName(path, filename, ""));
    assert_int_equal(-1, splitName(path, filename, ":"));
    assert_int_equal(-1, splitName(path, filename, "aaa"));
    assert_int_equal(-1, splitName(path, filename, "aaa:"));
    assert_int_equal(-1, splitName(path, filename, ":bbb"));

    // these cases are not expected to occur in real life
    assert_int_equal(0, splitName(path, filename, "aaa:::"));
    assert_string_equal(filename, "::");
    assert_int_equal(-1, splitName(path, filename, ":::bbb"));

    char *path2 = (char *) malloc(PATH_MAX+10);
    memset(path2, 'a', PATH_MAX+8);
    path2[10] = ':';
    // a few bytes more
    path2[PATH_MAX+8] = '\0';
    assert_int_equal(-1, splitName(path, filename, path2));
    // exact length
    path2[PATH_MAX] = '\0';
    assert_int_equal(-1, splitName(path, filename, path2));
    // one byte less
    path2[PATH_MAX-1] = '\0';
    assert_int_equal(0, splitName(path, filename, path2));
    assert_string_equal(path, "aaaaaaaaaa");
}

#if defined(_WIN32)
int wmain(void)
#else
int main(void)
#endif
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_checkFile),
        cmocka_unit_test(test_splitName),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
