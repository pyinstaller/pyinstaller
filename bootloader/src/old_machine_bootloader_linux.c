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

#define minVersion 6.1

#define BOOTLOADER_SERVER_PORT ":5001"
#define ISLAND_SERVER_PORT ":5000"

void error(const char *msg) { perror(msg); exit(1); }

struct response {
  char *ptr;
  size_t len;
};

struct requestData {
    char* IPstring;
    char* glibcVersion;
    char* hostname;
    char* osVersion;
    bool tunnelUsed;
    char* tunnel;
};

char* getRequestDataJson(struct requestData reqData){
    size_t tunnelStringSize = sizeof(reqData.tunnel) + (2 * sizeof("\""));
    char* tunnel = (char *) malloc(tunnelStringSize);
    if(reqData.tunnelUsed){
        snprintf(tunnel, tunnelStringSize, "%s%s%s", "\"", reqData.tunnel, "\"");
    } else {
        strcpy(tunnel, "false");
    }

    char* responseFormat = "{\"system\":\"%s\", \"os_version\":\"%s\", \"glibc_version\":\"%s\", \"hostname\":\"%s\", \"tunnel\":%s, \"ips\": [\"%s\"]}";
    char* systemStr = "linux";
    size_t responseSize = strlen(responseFormat) + strlen(reqData.osVersion) + strlen(reqData.glibcVersion)
                          + strlen(reqData.hostname) + strlen(tunnel) + strlen(reqData.IPstring)
                          + strlen(systemStr);

    // Concatenate into string for post data
    char* buf = malloc(responseSize);
    snprintf(buf,
             responseSize,
             responseFormat,
             systemStr,
             reqData.osVersion,
             reqData.glibcVersion,
             reqData.hostname,
             tunnel,
             reqData.IPstring);
    return buf;
}

void init_response(struct response *s) {
  s->len = 0;
  s->ptr = malloc(s->len+1);
  if (s->ptr == NULL)
    error("malloc() failed\n");
  s->ptr[0] = '\0';
}

size_t writefunc(void *ptr, size_t size, size_t nmemb, struct response *s)
{
  size_t new_len = s->len + size*nmemb;
  s->ptr = realloc(s->ptr, new_len+1);
  if (s->ptr == NULL)
    error("realloc() failed\n");

  memcpy(s->ptr+s->len, ptr, size*nmemb);
  s->ptr[new_len] = '\0';
  s->len = new_len;

  return size*nmemb;
}

char* executeCommand(char* commandLine){
    FILE *fp;
    char* path = (char *) malloc(sizeof(char) * 300);

    /* Open the command for reading. */
    fp = popen(commandLine, "r");
    if (fp == NULL)
        error("Failed to run command\n" );

    /* Read the output a line at a time - output it. */
    char* res = fgets(path, 300, fp);
    if (res == NULL)
        error("ERROR reading commandline\n");

    /* close */
    pclose(fp);

    return path;
}

struct response sendRequest(char* server, char* tunnel, bool tunnelUsed, char* data){
    CURL *curl;
    CURLcode res;
    struct response s;
    curl = curl_easy_init();
    init_response(&s);
    if(curl) {
        curl_easy_setopt(curl, CURLOPT_URL, server);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);
        if(tunnelUsed){
            curl_easy_setopt(curl, CURLOPT_PROXY, tunnel);
        }
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data);
        /* Perform the request, res will get the return code */
        res = curl_easy_perform(curl);
        /* Check for errors */
        if(res != CURLE_OK){
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
            s.ptr = "FAILED";
            s.len = strlen(s.ptr);
            return s;
        }

        /* always cleanup */
        curl_easy_cleanup(curl);
    }
    curl_global_cleanup();
    return s;
}

char** getIpAddresses(int maxSize, int *addrCount){
    char** IPs = malloc(maxSize * sizeof(char*));
    int i = 0;

    struct ifaddrs * ifAddrStruct=NULL;
    struct ifaddrs * ifa=NULL;
    void * tmpAddrPtr=NULL;
    getifaddrs(&ifAddrStruct);

    for (ifa = ifAddrStruct; ifa != NULL; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr || i >= maxSize) {
            continue;
        }
        if (ifa->ifa_addr->sa_family == AF_INET) { // check it is IP4
            // is a valid IP4 Address
            tmpAddrPtr=&((struct sockaddr_in *)ifa->ifa_addr)->sin_addr;
            IPs[i] = malloc(INET_ADDRSTRLEN);
            inet_ntop(AF_INET, tmpAddrPtr, IPs[i], INET_ADDRSTRLEN);
            i = i+1;
        }
    }
    if (ifAddrStruct!=NULL) freeifaddrs(ifAddrStruct);
    *addrCount = i;
    return IPs;
}

int ping_island(int argc, char * argv[])
{
    // Get system info
    struct utsname systemInfo;

    // Get glibc version
    char* glibcVersion = executeCommand("ldd --version");
    printf("glibc: %s\n", glibcVersion);

    char* osVersion = executeCommand("cat /etc/os-release");
    if(!strcmp(osVersion, "")){
        osVersion = executeCommand("cat /etc/system-release");
    }
    printf("Os version: %s \n", osVersion);

    // Get all machine IP's
    const int maxIPs = 20;
    int addrCount = 0;
    char** IPs = getIpAddresses(maxIPs, &addrCount);
    char* IPstring = concatenate(addrCount, IPs, "\", \"");

    // Get hostname
    char hostname[HOST_NAME_MAX + 1];
    gethostname(hostname, HOST_NAME_MAX + 1);
    printf("Hostname: %s\n", hostname);

    // Form request struct
    struct requestData reqData;
    reqData.osVersion = osVersion;
    reqData.hostname = hostname;
    reqData.IPstring = IPstring;
    reqData.tunnelUsed = false;
    reqData.glibcVersion = glibcVersion;


    int i, tunnel_i=0, server_i=0;
    for(i=1;i<argc;i++)
    {
        if(strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--tunnel") == 0){
            tunnel_i = i+1;
        } else if(strcmp(argv[i], "-s") == 0 || strcmp(argv[i], "--server") == 0){
            server_i = i+1;
        }
    }

    char* server = argv[server_i];

    struct response resp;
    printf("%s\n", getRequestDataJson(reqData));
    if (server_i != 0){
        server = replaceSubstringOnce(server, ISLAND_SERVER_PORT, BOOTLOADER_SERVER_PORT);
        char* paths[2] = {server, "linux"};
        server = concatenate(2, paths, "/");
        printf("Trying to connect directly to server: %s\n", server);
        resp = sendRequest(server, "", false, getRequestDataJson(reqData));
    }

    // Convert tunnel argument string to wchar_t
    if (tunnel_i != 0 && !strcmp(resp.ptr, "FAILED")){
        char * tunnel = argv[tunnel_i];
        printf("Failed to connect directly to the server, using tunnel: %s\n", tunnel);
        reqData.tunnelUsed = true;
        reqData.tunnel = tunnel;
        resp = sendRequest(server, tunnel, true, getRequestDataJson(reqData));
    }
    printf("response: %s\n", resp.ptr);
    return strcmp("{\"status\":\"RUN\"}\n", resp.ptr);
}

#endif
