import sys, os
import test6x
print "test6x.x is", test6x.x
txt = """\
x = %d
""" % (test6x.x + 1)
if hasattr(sys, 'frozen'):
    open(os.path.join(os.path.dirname(sys.executable), 'test6x.py'), 'w').write(txt)
else:
    open(test6x.__file__, 'w').write(txt)
reload(test6x)
print "test6x.x is now", test6x.x

    