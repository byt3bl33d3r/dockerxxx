import shlex
import struct
import httpx
from ptpython import embed

STDOUT = 1
STDERR = 2

async def debug_shell():
    await embed(locals=locals(), globals=globals(), return_asyncio_coroutine=True, patch_stdout=True)

def split_command(command):
    return shlex.split(command)

def get_raw_response_socket(client):
    if isinstance(client, httpx.AsyncClient):
        return client._transport._pool.connections[0]._connection._network_stream

    raise NotImplementedError

'''
https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/utils/socket.py#L92
'''

async def next_frame_header(socket):
    """
    Returns the stream and size of the next frame of data waiting to be read
    from socket, according to the protocol defined here:

    https://docs.docker.com/engine/api/v1.24/#attach-to-a-container
    """

    data = await socket.read(8)
    if not data:
        return (-1, -1)

    stream, actual = struct.unpack('>BxxxL', data)
    return (stream, actual)

async def frames_iter_no_tty(socket):
    """
    Returns a generator of data read from the socket when the tty setting is
    not enabled.
    """

    while True:
        (stream, n) = await next_frame_header(socket)
        if n < 0:
            break
        while n > 0:
            result = await socket.read(n)
            if result is None:
                continue
            data_length = len(result)
            if data_length == 0:
                # We have reached EOF
                return
            n -= data_length
            yield (stream, result)

async def frames_iter_tty(socket):
    """
    Return a generator of data read from the socket when the tty setting is
    enabled.
    """
    while True:
        result = await socket.read()
        if len(result) == 0:
            # We have reached EOF
            return
        yield result

async def frames_iter(socket, tty):
    """
    Return a generator of frames read from socket. A frame is a tuple where
    the first item is the stream number and the second item is a chunk of data.

    If the tty setting is enabled, the streams are multiplexed into the stdout
    stream.
    """
    if tty:
        return ((STDOUT, frame) async for frame in frames_iter_tty(socket))
    else:
        return frames_iter_no_tty(socket)
