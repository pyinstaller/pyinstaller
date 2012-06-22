
import sys
from wx.lib.pubsub import setuparg1
from wx.lib.pubsub import pub as Publisher

def OnMessage(message):
  print ("In the handler")
  if message.data == 762:
     print("pubsub success.")
     sys.exit(0)
  print("pubsub fail.")
  sys.exit(1)

Publisher.subscribe(OnMessage,"topic.subtopic")

Publisher.sendMessage("topic.subtopic",762)


