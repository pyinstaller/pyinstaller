/*
 * Glogal shared fuctions used in many bootloader files.
 *
 * Copyright (C) 2012, Martin Zibricky
 * Copyright (C) 2005, Giovanni Bajo
 * Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * In addition to the permissions in the GNU General Public License, the
 * authors give you unlimited permission to link or embed the compiled
 * version of this file into combinations with other programs, and to
 * distribute those combinations without any restriction coming from the
 * use of this file. (The General Public License restrictions do apply in
 * other respects; for example, they cover modification of the file, and
 * distribution when not linked into a combine executable.)
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 */


/* 
 * Enable use of Sean's Tool Box -- public domain -- http://nothings.org/stb.h.
 * File stb.h.
 * All functions starting with 'stb_' prefix are from this toolbox.
 *
 * This define has to be only in one C source file!
 */
//#define STB_DEFINE  1/* */                                                   
//#define STB_NO_REGISTRY 1 /* No need for Windows registry functions in stb.h. */


#include <stdarg.h>  /* va_list, va_start(), va_end() */
#include <stdio.h>


#ifdef WIN32
 #include <windows.h>
 #include <direct.h>
 #include <process.h>
 #include <io.h>
#endif


/* Text length of MessageBox(). */
#define MBTXTLEN 1024

/*
 * On Windows and with windowed mode (no console) show error messages
 * in message boxes. In windowed mode nothing is written to console.
 */

#if defined(WIN32) && defined(WINDOWED)
    void mbfatalerror(const char *fmt, ...)
    {
        char msg[MBTXTLEN];
        va_list args;

        va_start(args, fmt);
        _vsnprintf_s(msg, MBTXTLEN, MBTXTLEN, fmt, args);
        //vsnprintf(msg, MBTXTLEN, fmt, args);
        va_end(args);

        MessageBox(NULL, msg, "Fatal Error!", MB_OK | MB_ICONEXCLAMATION);
    }

    void mbothererror(const char *fmt, ...)
    {
        char msg[MBTXTLEN];
        va_list args;

        va_start(args, fmt);
        _vsnprintf_s(msg, MBTXTLEN, MBTXTLEN, fmt, args);
        //vsnprintf(msg, MBTXTLEN, fmt, args);
        va_end(args);

        MessageBox(NULL, msg, "Error!", MB_OK | MB_ICONWARNING);
    }
#endif /* WIN32 and WINDOWED */


/* Enable or disable debug output. */

#ifdef LAUNCH_DEBUG
    #if defined(WIN32) && defined(WINDOWED)
        void mbvs(const char *fmt, ...)
        {
            char msg[MBTXTLEN];
            va_list args;

            va_start(args, fmt);
            _vsnprintf_s(msg, MBTXTLEN, MBTXTLEN, fmt, args);
            //vsnprintf(msg, MBTXTLEN, fmt, args);
            /* Ensure message is timmed to fit the buffer. */
            //msg[MBTXTLEN-1] = '\0';
            va_end(args);

            MessageBox(NULL, msg, "Tracing", MB_OK);
        }
    #endif
#endif



