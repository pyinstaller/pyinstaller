import os
from distutils.sysconfig import get_python_lib

datas = [
    (os.path.join(get_python_lib(), 'weasyprint', 'css', 'html5_ua.css'),
     os.path.join('weasyprint', 'css'))
]
