@ECHO OFF
if '%1'=='' (%0 %cd%)
echo CWD - short: %~s1
echo CWD - long: %cd%
