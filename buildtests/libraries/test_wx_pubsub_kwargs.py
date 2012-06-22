
import sys
from wx.lib.pubsub import setupkwargs
from wx.lib.pubsub import pub as Publisher

def OnMessage(number):
  print ("In the handler")
  if number == 762:
     print("pubsub success.")
     sys.exit(0)
  print("pubsub fail.")
  sys.exit(1)

Publisher.subscribe(OnMessage,"topic.subtopic")

Publisher.sendMessage("topic.subtopic",number=762)


