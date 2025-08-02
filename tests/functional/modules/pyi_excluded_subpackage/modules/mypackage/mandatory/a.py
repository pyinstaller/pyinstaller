# This module contains an "unused" function (not called from anywhere in the package itself) that adds reference to the
# optional subpackage by importing a function from it. This simulates scenario where the said optional subpackage might
# be excluded by the top-level package hook; so that it is collected only if some external code (user's program or 3rd
# party package) is importing it.


def an_unused_function(ref_type):
    # A whole lot of different imports: subpackage vs submodule in it, function from package or submodule (the package
    # imports it from submodule), relative vs. absolute imports. The goal is to ensure that all of these are properly
    # interpreted by the exclusion mechanism, and end up being excluded as necessary.
    if ref_type == 0:
        import mypackage.optional
        return mypackage.optional.optional_function()
    elif ref_type == 1:
        from mypackage import optional
        return optional.optional_function()
    elif ref_type == 2:
        from .. import optional
        return optional.optional_function()
    elif ref_type == 3:
        import mypackage.optional.b
        return mypackage.optional.b.optional_function()
    elif ref_type == 4:
        from mypackage.optional import b
        return b.optional_function()
    elif ref_type == 5:
        from ..optional import b
        return b.optional_function()
    elif ref_type == 6:
        from mypackage.optional import optional_function
        return optional_function()
    elif ref_type == 7:
        from ..optional import optional_function
        return optional_function()
    elif ref_type == 8:
        from mypackage.optional.b import optional_function
        return optional_function()
    elif ref_type == 9:
        from ..optional.b import optional_function
        return optional_function()


# This symbol is imported by mypackage.mandatory, so we cannot get away by excluding this module.
an_important_symbol = 42
