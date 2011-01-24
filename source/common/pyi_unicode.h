
// the purpose of this include is to allow the selection of ANSI or UNICODE compiles.

#ifdef WIN32

#define UNICODE 
#define _UNICODE 
#include <tchar.h> 

#else

// for now, if we are not on a windows platform, just compile nonunicode.  

#include "tchar_nonwindows.h"


#endif