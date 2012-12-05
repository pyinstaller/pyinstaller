/*
 * On some platforms (e.g. Solaris, AIX) mkdtemp is not available.
 */
#ifndef __MKDTEMP__
#define __MKDTEMP__

static char* mkdtemp(char *template)
{
   if( ! mktemp(template) )
       return NULL;
   if( mkdir(template, 0700) )
       return NULL;
   return template;
}

#endif
