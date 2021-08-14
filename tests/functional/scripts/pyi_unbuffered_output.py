#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# A simple program for testing unbuffered mode of python stdout and stderr streams (both binary and text layers).
#
# The program periodically prints star ('*') character to a single line on the specified output stream (stdout or
# stderr). Once the selected number of stars have been printed, the end-of-transmission is signalled by 'E' character.
#
# In the unbuffered mode, the caller should receive the characters individually, and have enough time to process them.
# In the buffered mode, all printed characters including the terminating E will be received at once.
#
# NOTE: the unbuffered mode for text layers was introduced in Python 3.7.

import argparse
import time
import sys

# Argument parser
parser = argparse.ArgumentParser(description="Unbuffered stdio test")
parser.add_argument(
    '--num-stars',
    type=int,
    default=5,
    help="Number of star characters to print.",
)
parser.add_argument(
    '--output-stream',
    type=str,
    default='stdout',
    help="Output stream ('stdout' or 'stderr')",
)
parser.add_argument(
    '--stream-mode',
    type=str,
    default='text',
    help="Output stream mode ('text' or 'binary')",
)
args = parser.parse_args()

# Select output stream and mode
assert args.output_stream in {'stdout', 'stderr'}, f"Invalid output stream: {args.output_stream}!"
assert args.stream_mode in {'text', 'binary'}, f"Invalid output stream mode: {args.stream_mode}!"

stream = sys.stdout if args.output_stream == 'stdout' else sys.stderr
if args.stream_mode == 'binary':
    stream = stream.buffer  # Use binary layer
    STAR = b'*'
    EOT = b'E'
else:
    STAR = '*'
    EOT = 'E'

# Print the specified number of stars in a single line
for i in range(args.num_stars):
    stream.write(STAR)
    time.sleep(1)

# End-of-transmission
stream.write(EOT)
