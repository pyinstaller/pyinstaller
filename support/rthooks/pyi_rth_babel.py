import sys,os
d = "localedata"
if "_MEIPASS2" in os.environ:
    d = os.path.join(os.environ["_MEIPASS2"], d)
else:
    d = os.path.join(os.path.dirname(sys.argv[0]), d)

import babel.localedata
babel.localedata._dirname = os.path.abspath(d)
