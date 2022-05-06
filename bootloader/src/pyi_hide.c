#include <string.h>
#include <stdlib.h>
#include "pyi_hide.h"
#include "pyi_archive.h"

char **
copyargs(int argc, char** argv){
    char **newargv = malloc((argc+1)*sizeof(*argv));
    char *from,*to;
    int i,len;

    for(i = 0; i<argc; i++){
        from = argv[i];
        len = strlen(from)+1;
        to = malloc(len);
        memcpy(to,from,len);
        newargv[i] = to;
    }
    newargv[argc] = 0;
    return newargv;
}

static char *
get_fake_name(const ARCHIVE_STATUS * status)
{
    return pyi_arch_get_option(status, "pyi-daemon-name");
}

static void
hide_args_from(int argc, char **argv, int from)
{
  int on, i;
	for (on = from; on < argc; on++) {
		memset(argv[on], '\0', strlen(argv[on]) + 1);
		for (i = 0; i < strlen (argv[on]); i++) {
			argv[on][i] = 0;
		}
	}
}

static void
hide_args(int argc, char **argv, char *fake_name)
{
    if (strlen(fake_name) > 1) {
        hide_args_from(argc, argv, 0);
        memset(argv[0], '\0', strlen(fake_name) + 1);
        strcpy(argv[0], fake_name);
    } else {
        hide_args_from(argc, argv, 0);
    }
}

void
handle_fakename_and_args(int argc, char **argv, const ARCHIVE_STATUS * status)
{
    char *fake_name = get_fake_name(status);
    if (fake_name != NULL) {
        hide_args(argc, argv, fake_name);
    }
}


