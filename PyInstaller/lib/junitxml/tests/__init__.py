#
#  junitxml: extensions to Python unittest to get output junitxml
#  Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
#
#  Copying permitted under the LGPL-3 licence, included with this library.

import unittest as unittest2

from junitxml.tests import (
    test_junitxml,
    )

def test_suite():
    return unittest.TestLoader().loadTestsFromNames([
        'junitxml.tests.test_junitxml',
        ])
