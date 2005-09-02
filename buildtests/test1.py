print "test1 - hooks / strange pkg structures"
e1 = 'a_func from pkg2.a'
e2 = 'b_func from pkg2.b (pkg2/extra/b.py)'
e3 = 'notamodule from pkg2.__init__'
from pkg1 import *
t1 = a.a_func()
if t1 != e1:
    print "expected:", e1
    print "     got:", t1
t2 = b.b_func()
if t2 != e2:
    print "expected:", e2
    print "     got:", t2
t3 = notamodule()
if t3 != e3:
    print "expected:", e3
    print "     got:", t3
print "test1 complete"
