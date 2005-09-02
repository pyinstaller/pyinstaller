print "test3 - test 'f' option (just show os.environ)"
import os, sys
if sys.platform[:3] == 'win':
    print " sorry, no use / need for the 'f' option on Windows"
else:
    print " LD_LIBRARY_PATH %s" % os.environ.get('LD_LIBRARY_PATH', '<None!>')
print "test3 complete"
