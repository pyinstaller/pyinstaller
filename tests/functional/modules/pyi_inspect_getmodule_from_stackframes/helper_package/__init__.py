from . import helper_module


def test_call_chain():
    # Add another level of indirection...
    return helper_module.test_call_chain()
