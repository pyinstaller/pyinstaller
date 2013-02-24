WScript.Echo "Starting..."
set ob = CreateObject("MEInc.NextID")
WScript.Echo "created MEInc.NextID object"
dim num
num = ob.getNextID()
WScript.Echo "Got " + num



