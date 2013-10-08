#
#  junitxml: extensions to Python unittest to get output junitxml
#  Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
#
#  Copying permitted under the LGPL-3 licence, included with this library.

import unittest

from junitxml.tests import (
    test_junitxml,
    test_main,
    test_runner
    )

def test_suite():
    return unittest.TestLoader().loadTestsFromNames([
        'junitxml.tests.test_junitxml',
        'junitxml.tests.test_main',
        'junitxml.tests.test_runner'
        ])

if __name__ == '__main__':
    suite = test_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
