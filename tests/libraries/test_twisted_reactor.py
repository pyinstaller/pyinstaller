# Twisted is an event-driven networking engine.
#
# The 'reactor' is object that starts the eventloop.
# There are different types of platform specific reactors.
# Platform specific reactor is wrapped into twisted.internet.reactor module.

from twisted.internet import reactor

# Applications importing module twisted.internet.reactor might fail
# with error like:
#
#     AttributeError: 'module' object has no attribute 'listenTCP'
#
# Ensure default reactor was loaded - it has method 'listenTCP' to start server.
if not hasattr(reactor, 'listenTCP'):
    raise SystemExit('Twisted reactor not properly initialized.')
