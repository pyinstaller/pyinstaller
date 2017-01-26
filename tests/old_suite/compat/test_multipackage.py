import os
import sys


class Struct(object):
    def __init__(self, entries):
        self.__dict__.update(entries)

opts = {
    'all_with_crypto': False,
    'clean': False,
    'interactive_tests': False,
    'verbose': True,
    'run_known_fails': True,
}

args = []
for file in os.listdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'multipackage')):
    if file.endswith('.py'):
        args.append(os.path.join('multipackage', file))

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import runtests

for test in sorted(runtests.suite(Struct(opts), args)._tests, key=str):
    test_name = str(test).split(' ')[0].title()
    TestClass = type('TestClass', (type(test),), test.__dict__)
    TestClass._testcase = None
    exec('TestClass.{} = test._generic_test_function'.format(test._testMethodName))
    exec('{} = TestClass'.format(test_name))
    del TestClass

del test
