#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


def test_uvicorn(pyi_builder):
    """
    Check if uvicorn builds correctly.
    """
    pyi_builder.test_source(
        """
        import uvicorn
        import sys

        # as shown on:
        # https://www.uvicorn.org/#requests-responses

        async def app(scope, receive, send):
            '''
            Echo the method and path back in an HTTP response.
            '''
            assert scope['type'] == 'http'

            body = f'Received {scope["method"]} request to {scope["path"]}'
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [
                    [b'content-type', b'text/plain'],
                ]
            })
            await send({
                'type': 'http.response.body',
                'body': body.encode('utf-8'),
            })

        if __name__ == '__main__':
            # TODO: is sys.exit needed?
            #sys.exit(uvicorn.run(
            uvicorn.run(
                "test_source:app",
                host="127.0.0.1",
                port=8000,
                log_level="info"
            #))
            )
        """,
        pyi_args=['--hidden-import=test_source'],
        runtime=5,
    )
