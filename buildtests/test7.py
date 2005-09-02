import sys
import threading

def doit(nm):
    print nm, 'started'
    import test7x
    print nm, test7x.x

t1 = threading.Thread(target=doit, args=('t1',))    
t2 = threading.Thread(target=doit, args=('t2',))
t1.start()
t2.start()
doit('main')
t1.join()
t2.join()

