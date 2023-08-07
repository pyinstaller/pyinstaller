available_optional_dependencies = []
try:
    import email  # noqa: F401
    available_optional_dependencies.append("email")
except ImportError:
    pass
try:
    import gzip  # noqa: F401
    available_optional_dependencies.append("gzip")
except ImportError:
    pass
try:
    import pstats  # noqa: F401
    available_optional_dependencies.append("pstats")
except ImportError:
    pass
print("Available dependencies:", *available_optional_dependencies)
