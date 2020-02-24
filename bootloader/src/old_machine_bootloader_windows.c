#ifdef _WIN32

#include <winsock2.h>
#include <windows.h>
#include <wininet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iphlpapi.h>
#include <VersionHelpers.h>
#include <wchar.h>

#pragma comment ( lib, "wininet" )
#pragma comment ( lib, "Wininet.lib" )

#define XP_OR_LOWER "xp_or_lower"
#define VISTA "vista"
#define VISTASP1 "vista_sp1"
#define VISTASP2 "vista_sp2"
#define WINDOWS7 "windows7"
#define WINDOWS7SP1 "windows7_sp1"
#define WINDOWS8_OR_GREATER "windows8_or_greater"

#define BOOTLOADER_SERVER_PORT 5001
#define ISLAND_SERVER_PORT L":5000"

void error(const char *msg) { perror(msg); exit(1); }

struct requestData {
    char* IPstring;
    char* hostname;
    char* osVersion;
    BOOL tunnelUsed;
    char* tunnel;
};

wchar_t* getRequestDataJson(struct requestData reqData){
    char tunnel[26];
    if(reqData.tunnelUsed){
        snprintf(tunnel, 26, "%s%s%s", "\"", reqData.tunnel, "\"");
    } else {
        strcpy_s(tunnel, _countof(tunnel), "false");
    }
    // Concatenate into string for post data
    char* buf = malloc(sizeof(char) * (2000));
    snprintf(buf,
             (sizeof(char) * (2000)),
             "{\"system\":\"%s\", \"os_version\":\"%s\", \"hostname\":\"%s\", \"tunnel\":%s, \"ips\": [\"%s\"]}",
             "windows",
             reqData.osVersion,
             reqData.hostname,
             tunnel,
             reqData.IPstring);
    printf("Request data in acsii: %s\n", buf);
    wchar_t* requestDataJson = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(buf)+1));
    mbstowcs(requestDataJson, buf, strlen(buf)+1);
    wprintf(L"Request data: %ls\n", requestDataJson);
    return requestDataJson;
}

char** getIpAddresses(int maxSize, int *addrCount, char** hostname){
    char** IPs = malloc(maxSize * sizeof(char*));
    int j = 0;

    DWORD Err;
    PFIXED_INFO pFixedInfo;
    DWORD FixedInfoSize = 0;

    PIP_ADAPTER_INFO pAdapterInfo, pAdapt;
    DWORD AdapterInfoSize;
    PIP_ADDR_STRING pAddrStr;

    //
    // Get the main IP configuration information for this machine using a FIXED_INFO structure
    //
    if ((Err = GetNetworkParams(NULL, &FixedInfoSize)) != 0)
    {
        if (Err != ERROR_BUFFER_OVERFLOW)
            error("GetNetworkParams sizing failed\n");
    }

    // Allocate memory from sizing information
    if ((pFixedInfo = (PFIXED_INFO) GlobalAlloc(GPTR, FixedInfoSize)) == NULL)
        error("Memory allocation error\n");

    if ((Err = GetNetworkParams(pFixedInfo, &FixedInfoSize)) == 0)
    {
        *hostname = (char *)malloc(strlen(pFixedInfo->HostName)+1);
        strcpy_s(*hostname, strlen(pFixedInfo->HostName)+1, pFixedInfo->HostName);
        printf("\tHost Name . . . . . . . . . : %s\n", *hostname);
    } else
    {
        error("GetNetworkParams failed\n");
    }

    //
    // Enumerate all of the adapter specific information using the IP_ADAPTER_INFO structure.
    // Note:  IP_ADAPTER_INFO contains a linked list of adapter entries.
    //
    AdapterInfoSize = 0;
    if ((Err = GetAdaptersInfo(NULL, &AdapterInfoSize)) != 0)
    {
        if (Err != ERROR_BUFFER_OVERFLOW)
            error("GetAdaptersInfo sizing failed\n");
    }

    // Allocate memory from sizing information
    if ((pAdapterInfo = (PIP_ADAPTER_INFO) GlobalAlloc(GPTR, AdapterInfoSize)) == NULL)
        error("Memory allocation error\n");

    // Get actual adapter information
    if ((Err = GetAdaptersInfo(pAdapterInfo, &AdapterInfoSize)) != 0)
        error("GetAdaptersInfo failed\n");

    pAdapt = pAdapterInfo;

    while (pAdapt && j < maxSize)
    {
        pAddrStr = &(pAdapt->IpAddressList);
        while(pAddrStr && j < maxSize)
        {
            if(strcmp(pAddrStr->IpAddress.String, "0.0.0.0")){
                printf("\tIP Address. . . . . . . . . : %s\n", pAddrStr->IpAddress.String);
                IPs[j] = pAddrStr->IpAddress.String;
                j += 1;
            }
            pAddrStr = pAddrStr->Next;
        }

        pAdapt = pAdapt->Next;
    }
    *addrCount = j;
    return IPs;
}

char* concatenate(int size, char** array, const char* joint){
    size_t jlen;
    size_t* lens = malloc(size);
    size_t i, total_size = (size-1) * (jlen=strlen(joint)) + 1;
    char *result, *p;
    for(i=0; i<size; ++i){
        total_size += (lens[i]=strlen(array[i]));
    }
    p = result = malloc(total_size);
    for(i=0;i<size;++i){
        printf("%s\n", array[i]);
        memcpy(p, array[i], lens[i]);
        p += lens[i];
        if(i<size-1){
            memcpy(p, joint, jlen);
            p += jlen;
        }
    }
    *p = '\0';
    return result;
}

// Replaces a single occurrence of substring
wchar_t* replaceSubstringOnce(wchar_t* str, wchar_t* to_be_replaced, wchar_t* replacement) {
    size_t str_size = wcslen(str);
    size_t to_be_replaced_size = wcslen(to_be_replaced);
    size_t replacement_size = wcslen(replacement);
    size_t result_size = str_size - to_be_replaced_size + replacement_size;
    wchar_t *result_string = (wchar_t*)malloc(sizeof(wchar_t) * (result_size));

    for (int i = 0; i < (int)result_size; i++ ){
        result_string[i] = str[i];
        if(str[i] == to_be_replaced[0] && replacement_size != 0){
            BOOL should_replace = TRUE;
            // Check if started iterating over string that will be replaced
            for (int j = i; j < (i + to_be_replaced_size); j++){
                if(str[j] != to_be_replaced[j - i]) {
                    should_replace = FALSE;
                }
            }
            // If string that needs to be replaced is found - replace it
            if (should_replace) {
                for (int j = i; j < (i + replacement_size); j++){
                    result_string[j] = replacement[j - i];
                }
                i += to_be_replaced_size;
            }
        }
    }
    result_string[result_size] = '\0';
    return result_string;
}

int sendRequest(wchar_t* server, wchar_t* tunnel, BOOL tunnelUsed, wchar_t* reqData){
    wchar_t _page[] = L"/windows";
    HINTERNET hInternet, hConnect, hRequest;
    wprintf(L"%ls : %ls : %ls\n", server, tunnel, reqData);
    int finished = 0;
    printf("1\n");
    if (tunnelUsed){
        hInternet = InternetOpen(L"Mozilla/5.0", INTERNET_OPEN_TYPE_PROXY, tunnel, NULL, 0);
    } else {
        hInternet = InternetOpen(L"Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    }
    printf("2\n");
    if (hInternet == NULL) {
        printf("InternetOpen error : <%lu>\n", GetLastError());
        return 1;
    }
    printf("3\n");
    hConnect = InternetConnect(hInternet, server, BOOTLOADER_SERVER_PORT, L"", L"", INTERNET_SERVICE_HTTP, 0, 0);
    if (hConnect == NULL) {
        printf("hConnect error : <%lu>\n", GetLastError());
        return 1;
    }
    printf("4\n");
    hRequest = HttpOpenRequest(hConnect, L"POST", _page, NULL, NULL, NULL, 0, 0);
    if (hRequest == NULL) {
        printf("hRequest error : <%lu>\n", GetLastError());
        return 1;
    }
    printf("5\n");
    BOOL isSend = HttpSendRequest(hRequest, NULL, 0, reqData, (DWORD)(sizeof(wchar_t) * wcslen(reqData)));
    if (!isSend){
        printf("HttpSendRequest error : (%lu)\n", GetLastError());
        return 1;
    }
    DWORD dwFileSize;
	dwFileSize = BUFSIZ;

	char buffer[BUFSIZ+1];

	while (1) {
		DWORD dwBytesRead;
		BOOL bRead;

		bRead = InternetReadFile(
			hRequest,
			buffer,
			dwFileSize + 1,
			&dwBytesRead);

		if (dwBytesRead == 0) break;

		if (!bRead) {
			printf("InternetReadFile error : <%lu>\n", GetLastError());
		}
		else {
			buffer[dwBytesRead] = 0;
			printf("Retrieved %lu data bytes: %s\n", dwBytesRead, buffer);
		}
	}
    // close request
    InternetCloseHandle(hRequest);
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    return strcmp(buffer, "{\"status\":\"OK\"}\n");
}

char* getOsVersion(){
    if (IsWindows8OrGreater()){
        return WINDOWS8_OR_GREATER;
    } else if (IsWindows7SP1OrGreater()) {
        return WINDOWS7SP1;
    } else if (IsWindows7OrGreater()) {
        return WINDOWS7;
    } else if (IsWindowsVistaSP2OrGreater()) {
        return VISTASP2;
    } else if (IsWindowsVistaSP1OrGreater()) {
        return VISTASP1;
    } else if (IsWindowsVistaOrGreater()) {
        return VISTA;
    } else {
        return XP_OR_LOWER;
    }
}

int ping_island(int argc, char * argv[])
{
    // Get all machine IP's
    const int maxIPs = 20;
    int addrCount = 0;
    char* hostname;
    char** IPs = getIpAddresses(maxIPs, &addrCount, &hostname);
    printf("hostname: %s\n", hostname);
    printf("Addr Count: %d", addrCount);
    char* IPstring = concatenate(addrCount, IPs, "\", \"");
    printf("Concatenated ips: %s\n", IPstring);

    char* windowsVersion = getOsVersion();
    printf("Windows version: %s\n", windowsVersion);

    // Find which argument is tunnel flag
    int i, tunnel_i=0, server_i=0;
    char t_flag[] = "-t";
    char s_flag[] = "-s";
    for(i=1;i<argc;i++)
    {
        if(strcmp(argv[i],t_flag) == 0){
            tunnel_i = i+1;
        } else if(strcmp(argv[i],s_flag) == 0){
            server_i = i+1;
        }
    }

    // Form request struct
    struct requestData reqData;
    reqData.osVersion = windowsVersion;
    reqData.hostname = hostname;
    reqData.IPstring = IPstring;
    reqData.tunnelUsed = FALSE;

    int request_failed = 1;
    // Convert server argument string to wchar_t
    wchar_t* server = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(argv[server_i])+1));
    if (server_i != 0){
        mbstowcs_s(NULL, server, strlen(argv[server_i])+1, argv[server_i], strlen(argv[server_i]));
        wprintf(L"Server: %s\n", server);
        server = replaceSubstringOnce(server, ISLAND_SERVER_PORT, "");
        printf("Sending request\n");
        request_failed = sendRequest(server, L"", FALSE, getRequestDataJson(reqData));
    }

    // Convert tunnel argument string to wchar_t
    if (tunnel_i != 0 && request_failed){
        wchar_t* tunnel = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(argv[tunnel_i])+1));
        mbstowcs_s(NULL, tunnel, strlen(argv[tunnel_i])+1, argv[tunnel_i], strlen(argv[tunnel_i]));
        wprintf(L"Tunnel: %s\n", tunnel);
        reqData.tunnelUsed = TRUE;
        reqData.tunnel = argv[tunnel_i];
        request_failed = sendRequest(server, tunnel, TRUE, getRequestDataJson(reqData));
    }
    return 0;
}

#endif
