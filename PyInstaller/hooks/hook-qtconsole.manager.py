#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Hook for qtconsole library: https://github.com/jupyter/qtconsole
qtconsole provides a qt based terminal for the iPython kernel system.

See the list of kernels here:
https://github.com/jupyter/jupyter/wiki/Jupyter-kernels

I don't pretend to understand qtconsole, it is a little complex for me,
but I do understand that the class signature of:
QtKernelClientMixin(MetaQObjectHasTraits('NewBase', (HasTraits, SuperQObject), {}))
is probably difficult for PyInstaller. The culprit may also be were this class
is being used, in qtconsole.manager.QtKernelManager, as a calss attribute is has:
client_class = DottedObjectName('qtconsole.client.QtKernelClient')

Script to freeze:
https://github.com/jupyter/qtconsole/blob/master/examples/embed_qtconsole.py

Tested with (minimum conda env):
# Name                    Version                   Build  Channel
altgraph                  0.15                       py_0    conda-forge
backcall                  0.1.0                    py36_0
ca-certificates           2018.11.29           ha4d7672_0    conda-forge
certifi                   2018.11.29            py36_1000    conda-forge
colorama                  0.4.1                    py36_0
decorator                 4.3.0                    py36_0
future                    0.17.1                py36_1000    conda-forge
icu                       58.2                 ha66f8fd_1
ipykernel                 5.1.0            py36h39e3cac_0
ipython                   7.2.0            py36h39e3cac_0
ipython_genutils          0.2.0            py36h3c5d0ee_0
jedi                      0.13.2                   py36_0
jpeg                      9b                   hb83a4c4_2
jupyter_client            5.2.4                    py36_0
jupyter_core              4.4.0                    py36_0
libpng                    1.6.35               h2a8f88b_0
libsodium                 1.0.16               h9d3ae62_0
macholib                  1.11                       py_0    conda-forge
openssl                   1.0.2p            hfa6e2cd_1002    conda-forge
parso                     0.3.1                    py36_0
pefile                    2018.8.8                   py_0    conda-forge
pickleshare               0.7.5                    py36_0
pip                       18.1                     py36_0
prompt_toolkit            2.0.7                    py36_0
pycrypto                  2.6.1           py36hfa6e2cd_1002    conda-forge
pygments                  2.3.1                    py36_0
pyinstaller               3.4              py36h7602738_0    conda-forge
pyqt                      5.9.2            py36h6538335_2
PyQt5                     5.11.3                    <pip>
PyQt5_sip                 4.19.13                   <pip>
python                    3.6.8                h9f7ef89_0
python-dateutil           2.7.5                    py36_0
pywin32                   224             py36hfa6e2cd_1000    conda-forge
pywin32-ctypes            0.2.0                 py36_1000    conda-forge
pyzmq                     17.1.2           py36hfa6e2cd_0
qt                        5.9.6            vc14h1e9a669_2
qtconsole                 4.4.3                    py36_0
setuptools                40.6.3                   py36_0
sip                       4.19.8           py36h6538335_0
six                       1.12.0                   py36_0
sqlite                    3.26.0               he774522_0
tornado                   5.1.1            py36hfa6e2cd_0
traitlets                 4.3.2            py36h096827d_0
vc                        14.1                 h0510ff6_4
vs2015_runtime            14.15.26706          h3a45250_0
wcwidth                   0.1.7            py36h3d5aa90_0
wheel                     0.32.3                   py36_0
wincertstore              0.2              py36h7fe50ca_0
zeromq                    4.2.5                he025d50_1
zlib                      1.2.11               h62dcd97_3

Built with:
pyinstaller console.py -F --clean

Result:
It works! :relaxed:

"""

hiddenimports = [
    "qtconsole.client"
]
