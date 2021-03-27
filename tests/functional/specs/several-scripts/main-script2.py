try:
    DATA_FROM_RTHOOK
except:
    pass
else:
    raise RuntimeError("Can access data from earlier script.")
