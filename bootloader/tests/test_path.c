// -----------------------------------------------------------------------------
// Copyright (c) 2020, PyInstaller Development Team.
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
#include "pyi_path.h"

#include <setjmp.h> // required fo cmocka :-(
#include <cmocka.h>


static void test_dirname(void **state) {
    char result[PATH_MAX];

    assert_true(pyi_path_dirname(result, "/a1/bb/cc/dd"));
    assert_string_equal(result, "/a1/bb/cc");

    assert_true(pyi_path_dirname(result, "/a2/bb/cc/dd/"));
    assert_string_equal(result, "/a2/bb/cc");

    assert_true(pyi_path_dirname(result, "d3d"));
    assert_string_equal(result, PYI_CURDIRSTR);

    assert_true(pyi_path_dirname(result, "d5d/"));
    assert_string_equal(result, PYI_CURDIRSTR);

    assert_true(pyi_path_dirname(result, ""));
    assert_string_equal(result, PYI_CURDIRSTR);

    char *path2 = (char *) malloc(PATH_MAX+10);
    memset(path2, 'a', PATH_MAX+8);
    // a few bytes more
    path2[PATH_MAX+8] = '\0';
    assert_false(pyi_path_dirname(result, path2));
    // exact length
    path2[PATH_MAX] = '\0';
    assert_false(pyi_path_dirname(result, path2));
    // one byte less
    path2[PATH_MAX-1] = '\0';
    assert_true(pyi_path_dirname(result, path2));
}


static void test_basename(void **state) {
    char result[PATH_MAX];
    char input[PATH_MAX];
    // basename()'s second argument is not `const`, thus using a constant
    // string yields to segementation fault.

    strcpy(input, "/aa/bb/cc/d1d");
    pyi_path_basename(result, input);
    assert_string_equal(result, "d1d");

    strcpy(input, "d3dd");
    pyi_path_basename(result, input);
    assert_string_equal(result, "d3dd");

    /* These cases are not correctly handled by our implementation of
     * basename(). But this is okay, since we use basename() only to determine
     * the application path based on argv[0].
     *
    strcpy(input, "/aa/bb/cc/d2d/");
    pyi_path_basename(result, input);
    assert_string_equal(result, "d2d");

    strcpy(input, "d4dd/");
    pyi_path_basename(result, input);
    assert_string_equal(result, "d4dd");

    strcpy(input, "");
    pyi_path_basename(result, input);
    assert_string_equal(result, PYI_CURDIRSTR);
    */
}


static void test_join(void **state) {
    char path1[PATH_MAX];
    char path2[PATH_MAX];
    char result[PATH_MAX];
    char *r;

    r = pyi_path_join((char *)result, "lalala", "mememe");
    assert_ptr_equal(r, &result);
    assert_string_equal(result, "lalala/mememe");

    r = pyi_path_join((char *)result, "lalala/", "mememe");
    assert_ptr_equal(r, &result);
    assert_string_equal(result, "lalala/mememe");

    r = pyi_path_join((char *)result, "lalala/", "mememe/");
    assert_ptr_equal(r, &result);
    assert_string_equal(result, "lalala/mememe");

    r = pyi_path_join((char *)result, "lalala", "mememe/");
    assert_ptr_equal(r, &result);
    assert_string_equal(result, "lalala/mememe");

    r = pyi_path_join((char *)result, "lal/ala/", "mem/eme/");
    assert_ptr_equal(r, &result);
    assert_string_equal(result, "lal/ala/mem/eme");

    // First string empty is not handled
    r = pyi_path_join((char *)result, "", "mememe");
    assert_ptr_equal(r, &result);
    assert_string_equal(result, "/mememe");

    memset(path1, 'a', PATH_MAX); path1[PATH_MAX-1] = '\0';
    memset(path2, 'b', PATH_MAX); path2[PATH_MAX-1] = '\0';
    assert_int_equal(strlen(path1), PATH_MAX-1);
    assert_int_equal(strlen(path2), PATH_MAX-1);
    assert_ptr_equal(NULL, pyi_path_join(result, path1, path2));

    // tests near max lenght of path1
    assert_ptr_equal(NULL, pyi_path_join(result, path1, ""));
    path1[PATH_MAX-2] = '\0';
    assert_ptr_equal(NULL, pyi_path_join(result, path1, ""));
    path1[PATH_MAX-3] = '\0';
    assert_ptr_equal(r, pyi_path_join(result, path1, ""));
    assert_int_equal(strlen(result), PATH_MAX-2); // -2 no trailing slash in path1
    assert_ptr_equal(NULL, pyi_path_join(result, path1, "x"));
    path1[PATH_MAX-4] = '\0';
    assert_ptr_equal(r, pyi_path_join(result, path1, "x"));
    assert_int_equal(strlen(result), PATH_MAX-2); // -2 no trailing slash in path1
    assert_ptr_equal(NULL, pyi_path_join(result, path1, "xx"));

    // tests near max lenght of path2
    assert_ptr_equal(NULL, pyi_path_join(result, "", path2));
    assert_ptr_equal(NULL, pyi_path_join(result, "x", path2));
    path2[PATH_MAX-2] = '\0';
    assert_ptr_equal(NULL, pyi_path_join(result, "", path2)); // stash takes space!
    assert_ptr_equal(NULL, pyi_path_join(result, "x", path2));
    path2[PATH_MAX-3] = '\0';
    assert_ptr_equal(r, pyi_path_join(result, "", path2));
    assert_ptr_equal(NULL, pyi_path_join(result, "x", path2));
    path2[PATH_MAX-4] = '\0';
    assert_ptr_equal(r, pyi_path_join(result, "", path2));
    assert_ptr_equal(r, pyi_path_join(result, "x", path2));
    // we don't count exaclty if slashes are contained
    assert_int_equal(strlen(result), PATH_MAX-2);
    assert_ptr_equal(NULL, pyi_path_join(result, "xx", path2));
    path2[PATH_MAX-4] = '/';
    assert_int_equal(path2[strlen(path2)], 0);
    assert_int_equal(path2[strlen(path2)-1], '/');
    assert_ptr_equal(r, pyi_path_join(result, "", path2));
    // we don't count exaclty if slashes are contained
    assert_int_equal(strlen(result), PATH_MAX-3);
    assert_int_equal(result[strlen(result)-1], 'b'); // trailing slash removed
    assert_ptr_equal(NULL, pyi_path_join(result, "x", path2));
}


int pyi_search_path(char *result, const char *appname);

static void test_search_path(void **state) {
    char result[PATH_MAX];
    pyi_search_path(result, "my-app");
}


int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_dirname),
        cmocka_unit_test(test_basename),
        cmocka_unit_test(test_join),
        cmocka_unit_test(test_search_path),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
