#ifndef BOOTLOADER_SRC_OLD_MACHINE_COMMON_FUNCTIONS_H_
#define BOOTLOADER_SRC_OLD_MACHINE_COMMON_FUNCTIONS_H_

struct requestData {
	char* IPstring;
	char* glibcVersion;
	char* hostname;
	char* osVersion;
	char* tunnel;
};

#define ISLAND_SERVER_PORT ":5000"

#ifndef _WIN32
#define USER_AGENT "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
#else 
#define USER_AGENT L"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
#endif

char* concatenate(int size, char** array, const char* joint);
char* replaceSubstringOnce(char* str, char* to_be_replaced, char* replacement);
char* getRequestDataJson(struct requestData reqData, char* requestFormat, char* systemStr);
int parseFlags(int argc, char * argv[], int* server_i, int* tunnel_i);
void error(const char *msg);

#endif  // BOOTLOADER_SRC_OLD_MACHINE_COMMON_FUNCTIONS_H_
