#ifdef _WIN32
#include <windows.h>
#include <wininet.h>
#include <stdio.h>
#include <stdlib.h>

#pragma comment( lib, "wininet" )
#pragma comment (lib, "Wininet.lib")

int ping_island(int argc, char * argv[]);
#endif
