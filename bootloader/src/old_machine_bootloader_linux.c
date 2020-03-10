#ifndef _WIN32

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <gnu/libc-version.h>
#include <netdb.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <ifaddrs.h>
#include <curl/curl.h>
#include "old_machine_common_functions.h"

#define BOOTLOADER_SERVER_PORT ":5001"

struct response {
  char *ptr;
  size_t len;
};

void init_response(struct response *s) {
  s->len = 0;
  s->ptr = malloc(s->len+1);
  if (NULL == s->ptr) {
    error("malloc() failed\n");
  }
  s->ptr[0] = '\0';
}

size_t writefunc(void *ptr, size_t size, size_t nmemb, struct response *s) {
  size_t new_len = s->len + size*nmemb;
  s->ptr = realloc(s->ptr, new_len+1);
  if (s->ptr == NULL) {
    error("realloc() failed\n");
  }

  memcpy(s->ptr+s->len, ptr, size*nmemb);
  s->ptr[new_len] = '\0';
  s->len = new_len;

  return size*nmemb;
}

char* executeCommand(char* commandLine) {
    FILE *fp;
    const int maxOutputLength = 2400;
    char* fullOutput = (char *) malloc(maxOutputLength);
    if (fullOutput == NULL) {
        error("Memory allocation failed\n");
    }
    /* Open the command for reading. */
    fp = popen(commandLine, "r");
    if (NULL == fp) {
        free(fullOutput);
        return ("Failed to run command\n" );
    }

    /* Read the output a line at a time - output it. */
    char* res = fgets(fullOutput, maxOutputLength, fp);
    if (NULL == res) {
        free(fullOutput);
        return("ERROR reading commandline\n");
    }

    /* close */
    pclose(fp);

    // Reallocate less memory
    fullOutput = realloc(fullOutput, strlen(fullOutput)+1);
    if (NULL == fullOutput) {
        error("Realloc failed");
    }

    return fullOutput;
}

struct response sendRequest(char* server, char* tunnel, char* data) {
    CURL *curl;
    CURLcode res;
    struct response s;
    struct curl_slist *header = NULL;

    curl = curl_easy_init();
    init_response(&s);

    header = curl_slist_append(header, "Content-Type: application/json");
    char* user_agent_key = "User-Agent: ";
    char* user_agent = malloc(strlen(USER_AGENT_HEADER_CONTENT) + strlen(user_agent_key) + 1);
    if(user_agent == NULL) {
        error("Malloc failed!");
    }
    strcpy(user_agent, user_agent_key);
    strcat(user_agent, USER_AGENT_HEADER_CONTENT);
    header = curl_slist_append(header, user_agent);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, header);
    if (curl) {
        curl_easy_setopt(curl, CURLOPT_URL, server);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);
        if (tunnel != NULL) {
            curl_easy_setopt(curl, CURLOPT_PROXY, tunnel);
        }
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data);
        /* Perform the request, res will get the return code */
        res = curl_easy_perform(curl);
        /* Check for errors */
        if (res != CURLE_OK) {
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
            s.len = sizeof("FAILED");
            return s;
        }

        /* always cleanup */
        curl_easy_cleanup(curl);
    }
    curl_global_cleanup();
    return s;
}

char** getIpAddresses(int *addrCount) {
    char** IPs = NULL;
    int i = 0;

    struct ifaddrs * ifAddrStruct = NULL;
    struct ifaddrs * ifa = NULL;
    void * tmpAddrPtr = NULL;
    getifaddrs(&ifAddrStruct);

    for (ifa = ifAddrStruct; ifa != NULL; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr) {
            continue;
        }
        // check it is IP4 a valid IP4 Address
        if (ifa->ifa_addr->sa_family == AF_INET) {
            tmpAddrPtr = &((struct sockaddr_in *)ifa->ifa_addr)->sin_addr;
            i = i+1;
            IPs = (char**)realloc(IPs, (i+1)*sizeof(*IPs));
            if (NULL == IPs) {
                return NULL;
            }
            IPs[i-1] = (char*)malloc(INET_ADDRSTRLEN);
            if (NULL == IPs[i-1]) {
                return NULL;
            }
            inet_ntop(AF_INET, tmpAddrPtr, IPs[i-1], INET_ADDRSTRLEN);
        }
    }
    if (ifAddrStruct != NULL) {
        freeifaddrs(ifAddrStruct);
    }
    *addrCount = i;
    return IPs;
}

int ping_island(int argc, char * argv[]) {
    // Get system info
    struct utsname systemInfo;

    // Get glibc version
    char* glibcVersion = executeCommand("ldd --version");
    printf("glibc: %s\n", glibcVersion);

    char* osVersion = executeCommand("cat /etc/os-release");
    // Some old distributions like centos6 on AWS has a different os info path
    if (!strcmp(osVersion, "")) {
        osVersion = executeCommand("cat /etc/system-release");
    }
    printf("OS version: %s \n", osVersion);

    // Get all machine IP's
    int addrCount = 0;
    char** IPs = getIpAddresses(&addrCount);
    char* IPstring = "";
    if (NULL != IPs) {
        IPstring = concatenate(addrCount, IPs, "\", \"");
    }

    // Get hostname
    char hostname[HOST_NAME_MAX + 1];
    if (gethostname(hostname, HOST_NAME_MAX + 1) == -1) {
        hostname[0] = '\0';
    }
    printf("Hostname: %s\n", hostname);

    // Form request struct
    struct requestData reqData;
    reqData.osVersion = osVersion;
    reqData.hostname = hostname;
    reqData.IPstring = IPstring;
    reqData.tunnel = NULL;
    reqData.glibcVersion = glibcVersion;

    int tunnel_i, server_i;
    int parse_error = parseFlags(argc, argv, &server_i, &tunnel_i);
    if (parse_error) {
        error("Flag parse failed\n");
    }

    char* server = argv[server_i];

    struct response resp = {0};
    char* requestFormat = "{\"system\":\"%s\", \"os_version\":\"%s\", \"glibc_version\":\"%s\", \"hostname\":\"%s\", \"tunnel\":%s, \"ips\": [\"%s\"]}";
    char* systemStr = "linux";
    char* requestContents;
    if (server_i != 0) {
        server = replaceSubstringOnce(server, ISLAND_SERVER_PORT, BOOTLOADER_SERVER_PORT);
        char* paths[2] = {server, "linux"};
        server = concatenate(2, paths, "/");
        if (!strcmp(server, "")) {
            error("Failed to create path to server, quiting.\n");
        }
        requestContents = getRequestDataJson(reqData, requestFormat, systemStr);
        printf("Trying to connect directly to server: %s\n", server);
        resp = sendRequest(server, NULL, requestContents);
    }

    // Convert tunnel argument string to wchar_t
    if ((tunnel_i != 0) && (NULL != resp.ptr) && (!strcmp(resp.ptr, "FAILED"))) {
        char * tunnel = argv[tunnel_i];
        printf("Failed to connect directly to the server, using tunnel: %s\n", tunnel);
        reqData.tunnel = tunnel;
        requestContents = getRequestDataJson(reqData, requestFormat, systemStr);
        resp = sendRequest(server, tunnel, requestContents);
    }
    printf("response: %s\n", resp.ptr);

    // Even if island instructs not to run monkey, run anyways.
    // If monkey ends up being incompatible it will quit due to and error.
    return 0;
}

#endif
