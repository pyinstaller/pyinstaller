import urllib2

def div(a, b):
    try:
        return a/b

    except ZeroDivisionError, exc:
        print "Zero division!"
        return None

class MyClass (object):
    pass
