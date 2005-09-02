import versionInfo

import sys
if len(sys.argv) < 2:
    print "Usage: >python GrabVersion.py <exe>"
    print " where: <exe> is the fullpathname of a Windows executable."
    print " The printed output may be saved to a file,  editted and "
    print " used as the input for a verion resource on any of the "
    print " executable targets in an Installer config file."
    print " Note that only NT / Win2K can set version resources."
else:
    vs  = versionInfo.decode(sys.argv[1])
    print vs
                                            
