try:
    DATA_FROM_RTHOOK  # noqa: F821
except Exception:
    pass
else:
    raise RuntimeError("Can access data from earlier script.")
