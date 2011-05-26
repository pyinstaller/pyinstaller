# Verify packagin of PIL.Image. Specifically, the hidden import of FixTk
# importing tkinter is causing some problems.
try:
    from Image import fromstring
except ImportError:
    fromstring = "PIL missing!! Install PIL before running this test!"
print fromstring
