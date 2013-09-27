NextID.py

  ../../MakeCOMServer.py [options] NextID.py
  ../../Build.py DriveNextID.spec
  distdriveNextID\driveNextID --register
  testNextID.vbs
  python
  >>> import win32com.client
  >>> import pythoncom
  >>> o = win32com.client.Dispatch('MEInc.NextID', clsctx = pythoncom.CLSCTX_LOCAL_SERVER)
  >>> o.getNextID()
  'aaaab0000003'
  >>> ^Z
  distdriveNextID\driveNextID --unregister

the others:

  ../../Makespec [options] <script>
  <run it>
  <run it again - esp the genpy stuff>

The shell stuff doesn't work on my W2k box (permissions) or NT (old shell, old extensions).
testEnsureDispatch doesn't work under old versions (no EnsureDispatch).
