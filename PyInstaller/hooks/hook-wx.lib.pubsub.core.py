import os
import sys

def hook(mod):
   pth = str(mod.__path__[0])
   if os.path.isdir(pth):
      # if the user imported setuparg1, this is detected by the hook-wx.lib.pubsub.setuparg1.py hook.  That
      # hook sets sys.wxpubsub to "arg1", and we set the appropriate path here.
      protocol = getattr(sys,'pyinstaller_wxpubsub','kwargs')
      print "wx.lib.pubsub: Adding %s protocol path"%protocol
      mod.__path__.append(os.path.normpath(os.path.join(pth, protocol)))
     
   return mod
