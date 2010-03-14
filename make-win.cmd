@echo off
echo USAGE %~0 some-python-version
if "%VS90COMNTOOLS%"=="" (
	echo ERROR: VS90COMNTOOLS is not set or empty. Make sure Visual C++ 2008 is installed.
	exit /B 1
)
if not exist "%~dp1Scripts\scons.bat" (
	echo ERROR: %~dp1Scripts\scons.bat does not exist. Make sure SCons is installed.
	exit /B 2
)
setlocal
call "%VS90COMNTOOLS%..\..\VC\vcvarsall" %2
path %~dp1\Scripts;%~dp1;%PATH%
pushd "%~dp0"
scons
popd