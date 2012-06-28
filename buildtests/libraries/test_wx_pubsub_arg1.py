
import sys
from wx.lib.pubsub import setuparg1
from wx.lib.pubsub import pub as Publisher

def OnMessage(message):
  print ("In the handler")
  if message.data == 762:
     sys.exit(0)
  else:
     raise SystemExit('wx_pubsub_arg1 failed.')

Publisher.subscribe(OnMessage,"topic.subtopic")

Publisher.sendMessage("topic.subtopic",762)


