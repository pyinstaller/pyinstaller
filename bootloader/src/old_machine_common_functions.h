struct requestData {
	char* IPstring;
	char* glibcVersion;
	char* hostname;
	char* osVersion;
	char* tunnel;
};

char* concatenate(int size, char** array, const char* joint);
char* replaceSubstringOnce(char* str, char* to_be_replaced, char* replacement);
char* getRequestDataJson(struct requestData reqData, char* requestFormat, char* systemStr);
