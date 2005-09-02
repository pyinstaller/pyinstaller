print "test4 - unbufferred"
print "type: 123456<enter>"
print "should see: 12345"
print "type: <enter>"
print "if unbuffered should see: 6"
print "if NOT unbuffered, should see nothing"
print "Q to quit"
import sys
while 1:
    data = sys.stdin.read(5)
    sys.stdout.write(data)
    if 'Q' in data:
        break
print "test4 - done"
