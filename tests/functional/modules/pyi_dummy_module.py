"""
    pyi_dummy_module

    This module exists only so it can be imported and its __file__ inspected in
    the test `test_compiled_filenames`
"""


def dummy():
    pass


class DummyClass(object):
    def dummyMethod(self):
        pass
