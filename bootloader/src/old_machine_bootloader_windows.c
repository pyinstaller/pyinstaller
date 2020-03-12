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

#include <shlwapi.h>
#include "old_machine_common_functions.h"

#pragma comment(lib, "wininet")
#pragma comment(lib, "Wininet.lib")
#pragma comment(lib, "Shlwapi.lib")

#define XP_OR_LOWER "xp_or_lower"
#define VISTA "vista"
#define VISTASP1 "vista_sp1"
#define VISTASP2 "vista_sp2"
#define WINDOWS7 "windows7"
#define WINDOWS7SP1 "windows7_sp1"
#define WINDOWS8_OR_GREATER "windows8_or_greater"

#define BOOTLOADER_SERVER_PORT 5001

int shouldMonkeyRun(char* windowsVersion) {
    if (!strcmp(windowsVersion, XP_OR_LOWER))
        return 1;
    if (!strcmp(windowsVersion, VISTA))
        return 1;
    if (!strcmp(windowsVersion, VISTASP1))
        return 1;
    if (!strcmp(windowsVersion, VISTASP2))
        return 1;
    else
        return 0;
}

char** getIpAddresses(int *addrCount, char** hostname) {
    int num_addresses = 0;
    *addrCount = num_addresses;
    *hostname = (char *)malloc(2);
    if (NULL == *hostname) {
        error("Malloc failure!");
    }
    strcpy_s(*hostname, 1, "");

    DWORD Err;
    PFIXED_INFO pFixedInfo;
    ULONG FixedInfoSize = 0;

    PIP_ADAPTER_INFO pAdapterInfo, pAdapt;
    DWORD AdapterInfoSize;
    PIP_ADDR_STRING pAddrStr;

    pFixedInfo = (FIXED_INFO *) malloc(sizeof(FIXED_INFO));
    if (NULL == pFixedInfo) {
        error("Memory allocation error\n");
    }
    FixedInfoSize = sizeof (FIXED_INFO);

    if (GetNetworkParams(pFixedInfo, &FixedInfoSize) == ERROR_BUFFER_OVERFLOW) {
        free(pFixedInfo);
        pFixedInfo = (FIXED_INFO *) malloc(FixedInfoSize);
        if (NULL == pFixedInfo) {
            error("Error allocating memory needed to call GetNetworkParams\n");
        }
    }

    Err = GetNetworkParams(pFixedInfo, &FixedInfoSize);
    if (Err == 0) {
        *hostname = (char *)malloc(strlen(pFixedInfo->HostName) + 1);
        if (NULL == *hostname) {
            free(pFixedInfo);
            error("Malloc failure!");
        }
        strcpy_s(*hostname, strlen(pFixedInfo->HostName)+1, pFixedInfo->HostName);
        printf("\tHost Name . . . . . . . . . : %s\n", *hostname);
    } else {
        free(pFixedInfo);
        printf("GetNetworkParams failed\n");
        return NULL;
    }

    free(pFixedInfo);
    pFixedInfo = NULL;

    // Enumerate all of the adapter specific information using the IP_ADAPTER_INFO structure.
    // Note:  IP_ADAPTER_INFO contains a linked list of adapter entries.
    AdapterInfoSize = 0;
    Err = GetAdaptersInfo(NULL, &AdapterInfoSize);
    if (Err != 0) {
        if (Err != ERROR_BUFFER_OVERFLOW) {
            printf("GetAdaptersInfo sizing failed\n");
            return NULL;
        }
    }

    // Allocate memory from sizing information
    pAdapterInfo = (PIP_ADAPTER_INFO)malloc(AdapterInfoSize);
    if (NULL == pAdapterInfo) {
        error("Memory allocation error\n");
    }

    char** IPs = malloc(AdapterInfoSize);
    // Get actual adapter information
    Err = GetAdaptersInfo(pAdapterInfo, &AdapterInfoSize);
    if (Err != 0) {
        free(IPs);
        printf("GetAdaptersInfo failed\n");
        return NULL;
    }

    pAdapt = pAdapterInfo;

    while (pAdapt) {
        pAddrStr = &(pAdapt->IpAddressList);
        while (pAddrStr) {
            if (strcmp(pAddrStr->IpAddress.String, "0.0.0.0")) {
                printf("\tIP Address. . . . . . . . . : %s\n", pAddrStr->IpAddress.String);
                char * duplicate_string = malloc(strlen(pAddrStr->IpAddress.String));
                if (NULL == duplicate_string) {
                    free(IPs);
                    error("Memory allocation error\n");
                }
                strcpy(duplicate_string, pAddrStr->IpAddress.String);
                IPs[num_addresses] = duplicate_string;
                num_addresses += 1;
            }
            pAddrStr = pAddrStr->Next;
        }

        pAdapt = pAdapt->Next;
    }
    free(pAdapterInfo);
    *addrCount = num_addresses;

    return IPs;
}

int sendRequest(wchar_t* server, wchar_t* tunnel, wchar_t* reqData) {
    const wchar_t page[] = L"/windows";
    const wchar_t requestType[] = L"POST";
    char* buffer = NULL;
    HINTERNET hInternet = NULL, hConnect = NULL, hRequest = NULL;
    wprintf(L"%ls : %ls : %ls\n", server, tunnel, reqData);

    wchar_t* userAgent = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(USER_AGENT_HEADER_CONTENT) + 1));
    if (NULL == userAgent){
        error("Memory allocation failed\n");
    }
    mbstowcs_s(NULL, userAgent, strlen(USER_AGENT_HEADER_CONTENT) + 1, USER_AGENT_HEADER_CONTENT, strlen(USER_AGENT_HEADER_CONTENT) + 1);

    int finished = 0;
    if (NULL != tunnel) {
        hInternet = InternetOpen(userAgent,
                                 INTERNET_OPEN_TYPE_PROXY,
                                 tunnel,
                                 NULL,
                                 0);
    } else {
        hInternet = InternetOpen(userAgent,
                                 INTERNET_OPEN_TYPE_DIRECT,
                                 NULL,
                                 NULL,
                                 0);
    }
    if (NULL == hInternet) {
        printf("InternetOpen error : <%lu>\n", GetLastError());
        goto cleanUp;
    }
    hConnect = InternetConnect(hInternet,
                               server,
                               BOOTLOADER_SERVER_PORT,
                               L"",
                               L"",
                               INTERNET_SERVICE_HTTP,
                               0,
                               0);
    if (NULL == hConnect) {
        printf("hConnect error : <%lu>\n", GetLastError());
        goto cleanUp;
    }
    hRequest = HttpOpenRequest(hConnect,
                               requestType,
                               page, NULL,
                               NULL, NULL, 0, 0);
    if (NULL == hRequest) {
        printf("hRequest error : <%lu>\n", GetLastError());
        goto cleanUp;
    }
    wchar_t* additionalHeaders = L"Content-Type: application/json\nAccept-Encoding: gzip, deflate, br\nAccept-Language: lt,en-US;q=0.9,en;q=0.8,ru;q=0.7,pl;q=0.6";
    BOOL isSent = HttpSendRequest(hRequest, additionalHeaders,
                                  0, reqData,
                                  (DWORD)(sizeof(wchar_t) * wcslen(reqData)));
    if (!isSent) {
        printf("HttpSendRequest error : (%lu)\n", GetLastError());
        goto cleanUp;
    }
    DWORD dwFileSize;
    dwFileSize = BUFSIZ;
    buffer = malloc(BUFSIZ+1);
    if (NULL == buffer) {
        error("Memory allocation failed\n");
    }
    while (1) {
        DWORD dwBytesRead;
        BOOL bRead;

        bRead = InternetReadFile(
            hRequest,
            buffer,
            dwFileSize + 1,
            &dwBytesRead);


        if (!bRead) {
            printf("InternetReadFile error : <%lu>\n", GetLastError());
        }
        if (dwBytesRead == 0) {
            break;
        } else {
            buffer[dwBytesRead] = 0;
            printf("Retrieved %lu data bytes: %s\n", dwBytesRead, buffer);
        }
    }

    cleanUp:
        if (NULL != hRequest) {
            InternetCloseHandle(hRequest);
        }
        if (NULL != hConnect) {
            InternetCloseHandle(hRequest);
        }
        if (NULL !=  hRequest) {
            InternetCloseHandle(hRequest);
        }
        if (NULL != buffer) {
            return strcmp(buffer, "{\"status\":\"RUN\"}\n");
        } else {
            return 1;
        }
}

char* getOsVersion() {
    if (IsWindows8OrGreater()) {
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

int ping_island(int argc, char * argv[]) {
    // Get all machine IP's
    int addrCount = 0;
    char* hostname = NULL;
    char** IPs = getIpAddresses(&addrCount, &hostname);
    char* IPstring;
    if (NULL != IPs) {
        IPstring = concatenate(addrCount, IPs, "\", \"");
    } else {
        IPstring = '\0';
    }

    char* windowsVersion = getOsVersion();
    printf("Windows version: %s\n", windowsVersion);

    // Find which argument is tunnel flag
    int tunnel_i, server_i;
    int parse_error = parseFlags(argc, argv, &server_i, &tunnel_i);
    if (parse_error) {
        error("Flag parse failed\n");
    }

    // Form request struct
    struct requestData reqData;
    reqData.osVersion = windowsVersion;
    reqData.hostname = hostname;
    reqData.IPstring = IPstring;
    reqData.tunnel = NULL;
    reqData.glibcVersion = NULL;


    BOOL requiredDllPresent = TRUE;
    // If running on windows 7 monkey will crash if system is not updated
    if (!strcmp(windowsVersion, WINDOWS7SP1) || !strcmp(windowsVersion, WINDOWS7)) {
        TCHAR windir[MAX_PATH] = {0};
        if (GetSystemDirectory(windir, MAX_PATH)) {
            wchar_t* dllPath = L"\\Ucrtbase.dll";
            wchar_t* absDllPath = malloc(MAX_PATH);
            if (absDllPath == NULL) {
                error("Memory allocation failed\n");
            }
            wcscpy(absDllPath, windir);
            wcscat(absDllPath, dllPath);
            requiredDllPresent = PathFileExistsW(absDllPath);
        }
    }

    int request_failed = 1;
    // Convert server argument string to wchar_t
    if (server_i == 0) {
        error("Server argument not passed\n");
    }
    wchar_t* serverW;

    char* responseFormat = "{\"system\":\"%s\", \"os_version\":\"%s\", \"hostname\":\"%s\", \"tunnel\":%s, \"ips\": [\"%s\"]}";
    char* systemStr = "windows";
    char* requestContents;
    wchar_t* requestContentsW;
    if (server_i != 0) {
        char * server = replaceSubstringOnce(argv[server_i], ISLAND_SERVER_PORT, "");
        serverW = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(server) + 1));
        if (NULL == serverW) {
            free(server);
            error("Memory allocation failed\n");
        }
        mbstowcs_s(NULL, serverW, strlen(server) + 1, server, strlen(server) + 1);

        requestContents = getRequestDataJson(reqData, responseFormat, systemStr);
        requestContentsW = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(requestContents) + 1));
        if (NULL == requestContentsW) {
            free(server);
            error("Memory allocation failed\n");
        }
        mbstowcs_s(NULL, requestContentsW, strlen(requestContents) + 1, requestContents, strlen(requestContents) + 1);
        printf("Sending request\n");
        request_failed = sendRequest(serverW, NULL, requestContentsW);
        free(server);
    }

    // Convert tunnel argument string to wchar_t
    if (tunnel_i != 0 && serverW != NULL && request_failed) {
        size_t tunnelStrLen = strlen(argv[tunnel_i]) + 1;
        wchar_t* tunnel = (wchar_t*)malloc(sizeof(wchar_t) * (tunnelStrLen));
        if (NULL == tunnel) {
            error("Memory allocation failed\n");
        }
        mbstowcs_s(NULL, tunnel, tunnelStrLen, argv[tunnel_i], tunnelStrLen);
        wprintf(L"Tunnel: %s\n", tunnel);
        reqData.tunnel = argv[tunnel_i];

        requestContents = getRequestDataJson(reqData, responseFormat, systemStr);
        requestContentsW = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(requestContents) + 1));
        if (requestContentsW == NULL) {
            free(tunnel);
            error("Memory allocation failed\n");
        }
        mbstowcs_s(NULL, requestContentsW, strlen(requestContents) + 1, requestContents, strlen(requestContents) + 1);
        request_failed = sendRequest(serverW, tunnel, requestContentsW);
        free(tunnel);
    }
    if (!requiredDllPresent) {
        return 1;
    } else {
        return shouldMonkeyRun(windowsVersion);
    }
}

#endif
