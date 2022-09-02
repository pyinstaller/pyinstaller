from . import submodule_feature3

# Try importing two other custom top-level modules, and provide boolean flags indicating their availability.
# Feature #1
feature1_available = False
try:
    import mymodule_feature1  # noqa: F401
    feature1_available = True
except ImportError:
    pass

# Feature #2
feature2_available = False
try:
    import mymodule_feature2  # noqa: F401
    feature2_available = True
except ImportError:
    pass

# Feature #3: imported via sub-module from this pacakge, which in turn tries to import submodule from mymodule_feature3.
feature3_available = submodule_feature3.feature3_available
