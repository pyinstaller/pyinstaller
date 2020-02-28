#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "old_machine_common_functions.h"

char* getRequestDataJson(struct requestData reqData, char* requestFormat, char* systemStr){
    char* tunnel;
    if(reqData.tunnel != NULL){
		size_t tunnelStringSize = sizeof(reqData.tunnel) + (2 * sizeof("\""));
		tunnel = (char *)malloc(tunnelStringSize);
        snprintf(tunnel, tunnelStringSize, "%s%s%s", "\"", reqData.tunnel, "\"");
    } else {
		tunnel = (char *)malloc(sizeof("false"));
        strcpy_s(tunnel, sizeof("false"), "false");
    }

    size_t responseSize = strlen(requestFormat) + strlen(reqData.osVersion) + strlen(reqData.hostname) +
					      strlen(tunnel) + strlen(reqData.IPstring) + strlen(systemStr);

	if (reqData.glibcVersion != NULL) {
		responseSize += strlen(reqData.glibcVersion);
	}

    // Concatenate into string for post data
    char* buf = malloc(responseSize);
	if (reqData.glibcVersion != NULL) {
		snprintf(buf,
			responseSize,
			requestFormat,
			systemStr,
			reqData.osVersion,
			reqData.glibcVersion,
			reqData.hostname,
			tunnel,
			reqData.IPstring);
	}
	else {
		snprintf(buf,
			responseSize,
			requestFormat,
			systemStr,
			reqData.osVersion,
			reqData.hostname,
			tunnel,
			reqData.IPstring);
	}
    return buf;
}

char* concatenate(int size, char** array, const char* joint){
    size_t jlen = strlen(joint);
    size_t* lens = malloc(size * sizeof(size_t));
	if (lens == NULL) {
		return '\0';
	}
    size_t i;
    size_t total_size = (size-1) * (jlen) + 1;
    char *result, *p;
    for(i=0; i<size; ++i){
		lens[i] = strlen(array[i]);
        total_size += lens[i];
    }
    p = result = malloc(total_size);
    for(i=0; i<size; ++i){
        memcpy(p, array[i], lens[i]);
        p += lens[i];
        if(i < (size-1)){
            memcpy(p, joint, jlen);
            p += jlen;
        }
    }
    *p = '\0';
    return result;
}

// Replaces a single occurrence of substring
char* replaceSubstringOnce(char* str, char* to_be_replaced, char* replacement) {
    size_t str_size = strlen(str);
    size_t to_be_replaced_size = strlen(to_be_replaced);
    size_t replacement_size = strlen(replacement);
    size_t result_size = str_size - to_be_replaced_size + replacement_size;
    char *result_string = (char*)malloc(sizeof(char) * (result_size));
    int substringReplaced = 0;

    for (int i = 0; i < (int)result_size; i++ ){
        if(substringReplaced){
            break;
        }
        result_string[i] = str[i];
        if(str[i] == to_be_replaced[0] && replacement_size != 0){
            int should_replace = 1;
            // Check if started iterating over string that will be replaced
            for (int j = i; j < (i + to_be_replaced_size); j++){
                if(str[j] != to_be_replaced[j - i]) {
                    should_replace = 0;
                }
            }
            // If string that needs to be replaced is found - replace it
            if (should_replace) {
                for (int j = i; j < (i + replacement_size); j++){
                    result_string[j] = replacement[j - i];
                }
                substringReplaced = 1;
            }
        }
    }
    result_string[result_size] = '\0';
     return result_string;
}
