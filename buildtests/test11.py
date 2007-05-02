# Verify packagin of PIL.Image. Specifically, the hidden import of FixTk
# importing tkinter is causing some problems.
from PIL.Image import fromstring
print fromstring
