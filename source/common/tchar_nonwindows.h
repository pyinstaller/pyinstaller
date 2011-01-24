#ifndef __TCHAR_NONWINDOWS_H__

#define TCHAR char
#define _T(x) x


#define _tcscpy     strcpy
#define _tcsncpy    strncpy
#define _tcschr     strchr
#define _tcscat     strcat
#define _tcslen     strlen
#define _tcscmp     strcmp
#define _tcsrchr    strrchr
#define _tcsstr     strstr
#define _tcstok     strtok
#define _tprintf    printf
#define _stprintf   sprintf
#define _vsntprintf vsnprintf

#define _tfopen     fopen
#define _tchmod     chmod
#define _ttempnam   _tempnam
#define _tmkdir     mkdir
#define _tstat      stat

#define _tgetenv    getenv
#define _tputenv    putenv

#endif