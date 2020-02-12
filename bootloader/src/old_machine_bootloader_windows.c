#include <windows.h>
#include <wininet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#pragma comment ( lib, "wininet" )
#pragma comment ( lib, "Wininet.lib" )

#define minVersion 6.1

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

struct versionInfo {
    DWORD MajorVersion;
    DWORD MinorVersion;
    DWORD Build;
    wchar_t* versionStr;
};

struct versionInfo getWindowsVersion(int size){

    DWORD dwVersion = 0;
    DWORD dwMajorVersion = 0;
    DWORD dwMinorVersion = 0;
    DWORD dwBuild = 0;

    dwVersion = GetVersion();

    // Get the Windows version.
    dwMajorVersion = (DWORD)(LOBYTE(LOWORD(dwVersion)));
    dwMinorVersion = (DWORD)(HIBYTE(LOWORD(dwVersion)));

    // Get the build number.
    if (dwVersion < 0x80000000)
        dwBuild = (DWORD)(HIWORD(dwVersion));

    wchar_t* versionStr = (wchar_t*)malloc(sizeof(wchar_t) * (size));
    snprintf(versionStr,
             size,
             "W%d.%d (%d)\n",
             dwMajorVersion,
             dwMinorVersion,
             dwBuild);
    struct versionInfo winVersionInfo = {dwMajorVersion, dwMinorVersion, dwBuild, versionStr};
    return winVersionInfo;
}

int sendRequest(wchar_t* server, wchar_t* tunnel, BOOL tunnelUsed, wchar_t* windowsVersion){

    wchar_t _page[] = L"/";
    HINTERNET hInternet, hConnect, hRequest;
    DWORD bytes_read;
    int finished = 0;
    if (tunnelUsed){
        hInternet = InternetOpen("Mozilla/5.0", INTERNET_OPEN_TYPE_PROXY, tunnel, NULL, 0);
    } else {
        hInternet = InternetOpen("Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    }

    if (hInternet == NULL) {
        printf("InternetOpen error : <%lu>\n", GetLastError());
        return 1;
    }

    hConnect = InternetConnect(hInternet, server, 5001, "", "", INTERNET_SERVICE_HTTP, 0, 0);
    if (hConnect == NULL) {
        printf("hConnect error : <%lu>\n", GetLastError());
        return 1;
    }

    hRequest = HttpOpenRequest(hConnect, L"POST", _page, NULL, NULL, NULL, NULL, 0);
    if (hRequest == NULL) {
        printf("hRequest error : <%lu>\n", GetLastError());
        return 1;
    }

    BOOL isSend = HttpSendRequest(hRequest, NULL, 0, windowsVersion, sizeof(windowsVersion));
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


int ping_island(int argc, char * argv[])
{

    struct versionInfo windowsVersion = getWindowsVersion(20);

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

    int request_failed = 1;
    // Convert server argument string to wchar_t
    wchar_t * server = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(argv[server_i])+1));
    if (server_i != 0){
        mbstowcs_s(NULL, server, strlen(argv[server_i])+1, argv[server_i], strlen(argv[server_i]));
        wprintf(L"Server: %s\n", server);
        server = replaceSubstringOnce(server, L":5000", L"");
        request_failed = sendRequest(server, L"", FALSE, windowsVersion.versionStr);
    }

    // Convert tunnel argument string to wchar_t
    if (tunnel_i != 0 && request_failed){
        wchar_t * tunnel = (wchar_t*)malloc(sizeof(wchar_t) * (strlen(argv[tunnel_i])+1));
        mbstowcs_s(NULL, tunnel, strlen(argv[tunnel_i])+1, argv[tunnel_i], strlen(argv[tunnel_i]));
        wprintf(L"Tunnel: %s\n", tunnel);
        request_failed = sendRequest(server, tunnel, TRUE, windowsVersion.versionStr);
    }

    float OS_version = (float)windowsVersion.MajorVersion + ((float)windowsVersion.MinorVersion / 10);
    if (OS_version > minVersion) {
        return 0;
    } else {
        return 1;
    }
}

