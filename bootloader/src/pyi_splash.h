/*
 * ****************************************************************************
 * Copyright (c) 2013-2020, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#ifndef PYI_SPLASH_H
#define PYI_SPLASH_H

/* Layout for the binary data packed inside the archive */
typedef struct _splash {
    /*
     * The size of the splash screen window. These size specifications are also
     * the dimensions of the splash screen image.
     *
     * Note:
     *  The two values must (for now) match the two fields img_width and
     *  img_height. They currently both specify the same size. They are
     *  separated, because in future versions the window may have to be
     *  larger than the image due to image scaling.
     */
    int wnd_width;
    int wnd_height;

    /*
     * Settings for the text that can be displayed on the splash screen.
     *
     * Specifies the rectangle in which the text is displayed. If the text
     * does not fit into the rectangle it will be clipped.
     * In addition the color of the text is passed
     *
     * On Windows:
     *    Although Windows only supports font names of up to 31 characters,
     *    the field for it is 64 characters so that future support
     *    on other platforms is not that limited.
     */
    struct {
        int left;
        int top;
        int right;
        int bottom;
    } txt_rect;
    int  txt_clr;
    int  txt_fontsize;
    char txt_fontname[64];

    /*
     * Information about the image data. This section will be the largest.
     * The format of the color values in the field 'bitmap' depends on the
     * platform-specific implementation.
     *
     * On Windows:
     *    - This structure is freed at runtime quite early, because
     *      all necessary information is copied into a runtime state struct.
     *    - At 32bit the RGB entries have to be pre-multiplied.
     *    - The bitmap data will be copied into a buffer managed by Windows
     *      itself at runtime.
     */
    int  img_datalen;
    int  img_width;
    int  img_height;
    char img_bit_count;
    char bitmap[1];
} SPLASH;

/*
 * Extract a SPLASH structure from the CArchive and returns it.
 * If none is provided NULL is returned.
 */
SPLASH *pyi_splash_get(ARCHIVE_STATUS *status);

/*
 * Launches the splash screen for various platforms.
 */
int pyi_splash_launch(SPLASH *splash);

/*
 * Create a inter-process communication mechanism.
 */
char *pyi_splash_setup_ipc();

#endif  /* PYI_SPLASH_H */
