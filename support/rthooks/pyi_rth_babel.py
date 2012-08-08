import os
import sys

d = "localedata"
d = os.path.join(sys._MEIPASS, d)

import babel.localedata
babel.localedata._dirname = d
