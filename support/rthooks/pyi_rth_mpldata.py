import sys,os
targetdir = os.environ.get("_MEIPASS2", os.path.abspath(os.path.dirname(sys.argv[0])))
os.environ["MATPLOTLIBDATA"] = os.path.join(targetdir, "mpl-data")
