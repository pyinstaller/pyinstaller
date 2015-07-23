# -*- coding: utf-8 -*-

# This test-case is for testing runtest's verbose output encoding.
#
# It outputs some non-ascii characters to stdout and stderr, encoding
# by the systems default encoding fot stdout resp. stderr. `runtest.py
# --verbose` should output the text correctly.

from __future__ import print_function

import sys

text = 'äüö'

# add some "garbage" to make the output easier to spot
print('stdout:', text, text, '-+' * 25)
print('stderr:', text, text, '-+' * 25, file=sys.stderr)
