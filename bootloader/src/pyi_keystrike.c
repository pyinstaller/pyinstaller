#ifdef _WIN32
#include <windows.h>
#include <tchar.h>
#include <stdio.h>
#include <limits.h>
#include "pyi_global.h"


LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION)
        // Block all keyboard input
        return 1;

    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

LRESULT CALLBACK LowLevelMouseProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0)
        return 1; // drop

    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

DWORD WINAPI check_lockfile_thread(LPVOID lpParam) {
    DWORD dwAttrib;
    HHOOK keyboardHook, mouseHook;
    char szTempFileName[MAX_PATH];  
    char szTempPath[MAX_PATH];  
    DWORD dwRetVal = 0;
    int loops = 0;

    dwRetVal = GetTempPathA(MAX_PATH, szTempPath); 

    if (dwRetVal > MAX_PATH || (dwRetVal == 0)) {
        FATALERROR("Keystrike GetTempPath failed (%d)\n", GetLastError());
        return -1;
    }

    // Keystrike lock file -- MUST MATCH what happens in terminator/client
    _snprintf(szTempFileName, MAX_PATH-1, "%s\\Keystrike\\terminator.lck", szTempPath);
    VS("Keystrike Temp Filename is: %s\n", szTempFileName);

    dwAttrib = GetFileAttributesA(szTempFileName);
    // Already exists?
    if(dwAttrib != INVALID_FILE_ATTRIBUTES && !(dwAttrib & FILE_ATTRIBUTE_DIRECTORY))
    {
        VS("Keystrike: Lock file already exists, attempting to remove...\n");
        if (!DeleteFileA (szTempFileName)) {
            FATALERROR("Keystrike Unable to remove stale lock file %s (%d)\n", szTempFileName, GetLastError());
            return -1;
        }
        // Removed... keep going
    }

    VS("Keystrike Installing hooks...\n");
    keyboardHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, NULL, 0);
    mouseHook = SetWindowsHookEx(WH_MOUSE_LL, LowLevelMouseProc, NULL, 0);

    while(1)
    {
        dwAttrib = GetFileAttributesA(szTempFileName);

        if(dwAttrib != INVALID_FILE_ATTRIBUTES && !(dwAttrib & FILE_ATTRIBUTE_DIRECTORY))
        {
            VS("Keystrike: Lockfile detected after %d loops! Removing hooks...\n", loops);
            UnhookWindowsHookEx(keyboardHook);
            UnhookWindowsHookEx(mouseHook);
            return 0;
        }

        Sleep(100);
        loops++;
    }

    // never reached
}

void keystrike_install_hook() {
    // Start the timer thread
    // Set up the low-level keyboard hook
    VS("Keystrike, setting up new thread\n");
    CreateThread(NULL, 0, check_lockfile_thread, NULL, 0, NULL);
}


#endif
