import os
import sys

from hookutils import eval_script

if sys.platform == 'win32':
    files = eval_script(os.path.join('utils', 'enchant-datafiles-finder.py'))
    datas = []  # data files in PyInstaller hook format
    for d in files:
        for f in d[1]:
            datas.append((f, d[0]))
