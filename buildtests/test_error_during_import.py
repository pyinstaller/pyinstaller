# See ticket #27: historically, PyInstaller was catching all errors during imports...
try:
	import error_during_import2
except KeyError:
	print "OK"
else:
	raise RuntimeError("failure!")

