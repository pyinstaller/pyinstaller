
// the purpose of this include is to allow the selection of ANSI or UNICODE compiles.

#ifdef WIN32

#define UNICODE 
#define _UNICODE 
#include <tchar.h> 

#else

// include our own cut-down version of tchar.h


#endif