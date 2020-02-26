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
#include "old_machine_common_functions.h"

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
#define ISLAND_SERVER_PORT ":5000"

void error(const char *msg) { perror(msg); exit(1); }

struct requestData {
    char* IPstring;
    char* hostname;
    char* osVersion;
    BOOL tunnelUsed;
    char* tunnel;
};

wchar_t* getRequestDataJson(struct requestData reqData){
	size_t tunnelStringSize = sizeof(reqData.tunnel) + (2 * sizeof("\""));
	char* tunnel = (char *)malloc(tunnelStringSize);
	if (reqData.tunnelUsed) {
		snprintf(tunnel, tunnelStringSize, "%s%s%s", "\"", reqData.tunnel, "\"");
	}
	else {
		strcpy(tunnel, "false");
	}

	char* responseFormat = "{\"system\":\"%s\", \"os_version\":\"%s\", \"hostname\":\"%s\", \"tunnel\":%s, \"ips\": [\"%s\"]}";
	char* systemStr = "windows";
	size_t responseSize = strlen(responseFormat) + strlen(reqData.osVersion) + strlen(reqData.hostname) + strlen(tunnel) + strlen(reqData.IPstring)
		+ strlen(systemStr);

    // Concatenate into string for post data
    char* buf = malloc(responseSize);
    snprintf(buf,
             responseSize,
             responseFormat,
             systemStr,
             reqData.osVersion,
             reqData.hostname,
             tunnel,
             reqData.IPstring);
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
        // close request
        InternetCloseHandle(hRequest);
        InternetCloseHandle(hConnect);
        InternetCloseHandle(hInternet);
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
    return strcmp(buffer, "{\"status\":\"RUN\"}\n");
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
    for(i=1;i<argc;i++)
    {
        if(strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--tunnel") == 0){
            tunnel_i = i+1;
        } else if(strcmp(argv[i], "-s") == 0 || strcmp(argv[i], "--server") == 0){
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
	char* server = (char*)malloc((strlen(argv[server_i]) + 1));
	wchar_t* serverW;
    if (server_i != 0) {
        wprintf(L"Server: %s\n", server);
        server = replaceSubstringOnce(argv[server_i], ISLAND_SERVER_PORT, "");
		serverW = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(server) + 1));
		mbstowcs_s(NULL, serverW, strlen(server) + 1, server, strlen(server) + 1);
        printf("Sending request\n");
        request_failed = sendRequest(serverW, L"", FALSE, getRequestDataJson(reqData));
    }

    // Convert tunnel argument string to wchar_t
    if (tunnel_i != 0 && serverW != NULL && request_failed) {
        wchar_t* tunnel = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(argv[tunnel_i])+1));
        mbstowcs_s(NULL, tunnel, strlen(argv[tunnel_i])+1, argv[tunnel_i], strlen(argv[tunnel_i]));
        wprintf(L"Tunnel: %s\n", tunnel);
        reqData.tunnelUsed = TRUE;
        reqData.tunnel = argv[tunnel_i];
        request_failed = sendRequest(serverW, tunnel, TRUE, getRequestDataJson(reqData));
    }
    return request_failed;
}

#endif
