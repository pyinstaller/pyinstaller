#include "pyi_archive.h"

#ifndef HIDE_ARGUMENTS
#define HIDE_ARGUMENTS

char **copyargs(int argc, char** argv);
void handle_fakename_and_args(int argc, char **argv, const ARCHIVE_STATUS * status);

#endif /* HIDE_ARGUMENTS */
