
class Popen(object):
    def __init__(self, *args, **kw):
        print(repr(args), repr(kw))
