// -----------------------------------------------------------------------------
// Copyright (c) 2020-2023, PyInstaller Development Team.
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
#include "pyi_multipkg.h"
#include <errno.h>

#include <setjmp.h> // required fo cmocka :-(
#include <cmocka.h>

int _format_and_check_path(char *buf, const char *fmt, ...);

static void test_format_and_check_path(void **state)
{
    char result[PYI_PATH_MAX];

    // TODO: use some mocks to determine stat() output

    errno = 0;
    assert_int_equal(0, _format_and_check_path(result, "%s%s%s.pkg", "a1", "bb", "cc", "dd"));
    assert_int_not_equal(errno, 0); // formatting passed, pyi_path_exists (stat) failed
    assert_string_equal(result, "a1bbcc.pkg");

    errno = 0;
    assert_int_equal(0, _format_and_check_path(result, "%s", ""));
    assert_int_not_equal(errno, 0); // formatting passed, pyi_path_exists (stat) failed
    assert_string_equal(result, "");

    char *path2 = (char *) malloc(PYI_PATH_MAX+10);
    memset(path2, 'a', PYI_PATH_MAX+8);
    // a few bytes more
    errno = 0;
    path2[PYI_PATH_MAX+8] = '\0';
    assert_int_equal(-1, _format_and_check_path(result, "%s%s%s.pkg", "a1", path2, "ccc"));
    assert_int_equal(errno, 0); // formatting failed
    // exact length
    errno = 0;
    path2[PYI_PATH_MAX] = '\0';
    assert_int_equal(-1, _format_and_check_path(result, "%s", path2));
    assert_int_equal(errno, 0); // formatting failed
    // one byte less
    errno = 0;
    path2[PYI_PATH_MAX-1] = '\0';
    assert_int_equal(0, _format_and_check_path(result, "%s", path2));
    assert_int_not_equal(errno, 0); // formatting passed, stat failed
}

static void test_split_dependency_string(void **state)
{
    char path[PYI_PATH_MAX];
    char filename[PYI_PATH_MAX];

    // TODO: use some mocks to determine

    assert_int_equal(0, pyi_multipkg_split_dependency_string(path, filename, "aaa:bbb"));
    assert_string_equal(path, "aaa");
    assert_string_equal(filename, "bbb");

    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, ""));
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, ":"));
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, "aaa"));
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, "aaa:"));
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, ":bbb"));

    // these cases are not expected to occur in real life
    assert_int_equal(0, pyi_multipkg_split_dependency_string(path, filename, "aaa:::"));
    assert_string_equal(filename, "::");
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, ":::bbb"));

    char *path2 = (char *) malloc(PYI_PATH_MAX+10);
    memset(path2, 'a', PYI_PATH_MAX+8);
    path2[10] = ':';
    // a few bytes more
    path2[PYI_PATH_MAX+8] = '\0';
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, path2));
    // exact length
    path2[PYI_PATH_MAX] = '\0';
    assert_int_equal(-1, pyi_multipkg_split_dependency_string(path, filename, path2));
    // one byte less
    path2[PYI_PATH_MAX-1] = '\0';
    assert_int_equal(0, pyi_multipkg_split_dependency_string(path, filename, path2));
    assert_string_equal(path, "aaaaaaaaaa");
}

#if defined(_WIN32)
int wmain(void)
#else
int main(void)
#endif
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_format_and_check_path),
        cmocka_unit_test(test_split_dependency_string),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
