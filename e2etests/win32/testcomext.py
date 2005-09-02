from win32com.shell import shell
import win32api
import pythoncom
import os
import sys

def CreateShortCut(Path, Target,Arguments = "", StartIn = "", Icon = ("",0), Description = ""):
    # Get the shell interface.
    sh = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, \
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)

    # Get an IPersist interface
    persist = sh.QueryInterface(pythoncom.IID_IPersistFile)

    # Set the data
    sh.SetPath(Target)
    sh.SetDescription(Description)
    sh.SetArguments(Arguments)
    sh.SetWorkingDirectory(StartIn)
    sh.SetIconLocation(Icon[0],Icon[1])
#    sh.SetShowCmd( win32con.SW_SHOWMINIMIZED)

    # Save the link itself.
    persist.Save(Path, 1)
    print "Saved to", Path

if __name__ == "__main__":
    try:
        TempDir = os.environ["TEMP"]
        WinRoot = os.environ["windir"]

        Path        =  TempDir
        Target      =  os.path.normpath(sys.executable)
        Arguments   =  ""
        StartIn     =  TempDir
        Icon        = ("", 0)
        Description = "py made shortcut"

        CreateShortCut(Path,Target,Arguments,StartIn,Icon,Description)
    except Exception, e:
        print "Failed!", e
        import traceback
        traceback.print_exc()
    raw_input("Press any key to continue...")