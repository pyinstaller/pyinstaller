#!/usr/bin/env python
import sys

try:
    import codecs
except ImportError:
    print "This test works only with Python versions that support Unicode"
    sys.exit(0)

a = u"foo bar"
au = codecs.getencoder("utf-8")(a)[0]
b = codecs.getdecoder("utf-8")(au)[0]
print "codecs working:", a == b
assert a == b
sys.exit(0)
