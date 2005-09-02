# Microsoft Developer Studio Project File - Name="runw" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 5.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Application" 0x0101

CFG=runw - Win32 Debug
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "runw.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "runw.mak" CFG="runw - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "runw - Win32 Release" (based on "Win32 (x86) Application")
!MESSAGE "runw - Win32 Debug" (based on "Win32 (x86) Application")
!MESSAGE 

# Begin Project
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
MTL=midl.exe
RSC=rc.exe

!IF  "$(CFG)" == "runw - Win32 Release"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "runw___W"
# PROP BASE Intermediate_Dir "runw___W"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "runw___W"
# PROP Intermediate_Dir "runw___W"
# PROP Ignore_Export_Lib 0
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /I "..\common" /I "f:\zlib113" /D "NDEBUG" /D "WIN32" /D "_WINDOWS" /D "HAVE_WARNINGS" /FD /c
# SUBTRACT CPP /O<none> /YX
# ADD BASE MTL /nologo /D "NDEBUG" /mktyplib203 /o NUL /win32
# ADD MTL /nologo /D "NDEBUG" /mktyplib203 /o NUL /win32
# ADD BASE RSC /l 0x409 /d "NDEBUG"
# ADD RSC /l 0x409 /d "NDEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LINK32=link.exe
# ADD BASE LINK32 kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib /nologo /subsystem:windows /machine:I386
# ADD LINK32 kernel32.lib user32.lib zlibstat.lib ws2_32.lib /nologo /subsystem:windows /machine:I386 /out:"..\..\support\runw.exe" /libpath:"f:\zlib113\zlibstat"
# SUBTRACT LINK32 /incremental:yes

!ELSEIF  "$(CFG)" == "runw - Win32 Debug"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 1
# PROP BASE Output_Dir "runw___0"
# PROP BASE Intermediate_Dir "runw___0"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 1
# PROP Output_Dir "runw___0"
# PROP Intermediate_Dir "runw___0"
# PROP Ignore_Export_Lib 0
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /Gm /GX /Zi /Od /D "WIN32" /D "_DEBUG" /D "_WINDOWS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /Gm /GX /Zi /Od /I "..\common" /I "f:\zlib113" /D "_DEBUG" /D "WIN32" /D "_WINDOWS" /D "HAVE_WARNINGS" /D "LAUNCH_DEBUG" /FD /c
# SUBTRACT CPP /YX
# ADD BASE MTL /nologo /D "_DEBUG" /mktyplib203 /o NUL /win32
# ADD MTL /nologo /D "_DEBUG" /mktyplib203 /o NUL /win32
# ADD BASE RSC /l 0x409 /d "_DEBUG"
# ADD RSC /l 0x409 /d "_DEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LINK32=link.exe
# ADD BASE LINK32 kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib /nologo /subsystem:windows /debug /machine:I386 /pdbtype:sept
# ADD LINK32 kernel32.lib user32.lib zlibstat.lib ws2_32.lib /nologo /subsystem:windows /debug /machine:I386 /out:"..\..\support\runw_d.exe" /pdbtype:sept /libpath:"f:\zlib113\zlibstat"

!ENDIF 

# Begin Target

# Name "runw - Win32 Release"
# Name "runw - Win32 Debug"
# Begin Source File

SOURCE=.\iconw.ico
# End Source File
# Begin Source File

SOURCE=..\common\launch.c
# End Source File
# Begin Source File

SOURCE=.\runw.rc
# End Source File
# Begin Source File

SOURCE=.\winmain.c
# End Source File
# End Target
# End Project
