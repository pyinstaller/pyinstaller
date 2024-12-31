# Feature #3: attempt to import submodule from mymodule_feature3
feature3_available = False
try:
    import mymodule_feature3.submodule1  # noqa: F401
    feature3_available = True
except ImportError:
    pass
