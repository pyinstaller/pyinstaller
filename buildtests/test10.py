# Verify packagin of PIL.Image. Specifically, the hidden import of FixTk
# importing tkinter is causing some problems.
from Image import fromstring
print fromstring
