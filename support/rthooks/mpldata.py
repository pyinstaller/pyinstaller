import os
targetdir = os.environ.get("_MEIPASS2", os.path.abspath("."))
os.environ["MATPLOTLIBDATA"] = os.path.join(targetdir, "mpl-data")
