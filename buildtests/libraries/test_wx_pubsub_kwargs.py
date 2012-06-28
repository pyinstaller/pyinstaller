
import sys
from wx.lib.pubsub import setupkwargs
from wx.lib.pubsub import pub as Publisher

def OnMessage(number):
  print ("In the handler")
  if number == 762:
     sys.exit(0)
  else: 
     raise SystemExit('wx_pubsub_kwargs failed.')

Publisher.subscribe(OnMessage,"topic.subtopic")

Publisher.sendMessage("topic.subtopic",number=762)


