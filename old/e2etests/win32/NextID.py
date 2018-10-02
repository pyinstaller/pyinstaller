# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 1999, 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

#import pythoncom
pycomCLSCTX_INPROC = 3
pycomCLSCTX_LOCAL_SERVER = 4
import os
d = {}

class NextID:
    _reg_clsid_ = '{25E06E61-2D18-11D5-945F-00609736B700}'
    _reg_desc_ = 'Text COM server'
    _reg_progid_ = 'MEInc.NextID'
    _reg_clsctx_ = pycomCLSCTX_INPROC | pycomCLSCTX_LOCAL_SERVER
    _public_methods_ = [
        'getNextID'
        ]
    def __init__(self):
        import win32api
        win32api.MessageBox(0, "NextID.__init__ started", "NextID.py")
        global d
        if sys.frozen:
            for entry in sys.path:
                if entry.find('?') > -1:
                    here = os.path.dirname(entry.split('?')[0])
                    break
            else:
                here = os.getcwd()
        else:
            here = os.path.dirname(__file__)
        self.fnm = os.path.join(here, 'id.cfg')
        try:
            d = eval(open(self.fnm, 'rU').read()+'\n')
        except:
            d = {
                'systemID': 0xaaaab,
                'highID': 0
            }
        win32api.MessageBox(0, "NextID.__init__ complete", "NextID.py")
    def getNextID(self):
        global d
        d['highID'] = d['highID'] + 1
        with open(self.fnm, 'w') as fp:
            fp.write(repr(d))
        return '%(systemID)-0.5x%(highID)-0.7x' % d

def RegisterNextID():
    from win32com.server import register
    register.UseCommandLine(NextID)

def UnRegisterNextID():
    from win32com.server import register
    register.UnregisterServer(NextID._reg_clsid_, NextID._reg_progid_)

if __name__ == '__main__':
    import sys
    if "/unreg" in sys.argv:
        UnRegisterNextID()
    elif "/register" in sys.argv:
        RegisterNextID()
    else:
        print("running as server")
        import win32com.server.localserver
        win32com.server.localserver.main()
        raw_input("Press any key...")
