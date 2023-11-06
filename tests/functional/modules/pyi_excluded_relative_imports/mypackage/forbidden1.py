from mypackage import _forbidden_enabled

if not _forbidden_enabled:
    raise Exception(f"Imported forbidden module {__name__}")
