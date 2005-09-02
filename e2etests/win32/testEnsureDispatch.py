# for older Pythons, we need to set up for the import of cPickle
import string
import copy_reg

import win32com.client.gencache
x = win32com.client.gencache.EnsureDispatch('ADOR.Recordset')
print x
x = None
#raw_input("Press any key to continue...")
