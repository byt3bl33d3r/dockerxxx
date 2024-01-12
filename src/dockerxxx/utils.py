import shlex
import struct
import httpx
import json
import warnings
from .errors import DockerException

try:
    from ptpython import embed
except ImportError:
    warnings.warn("ptpython was not found, debug shell won't work")

STDOUT = 1
STDERR = 2
STREAM_HEADER_SIZE_BYTES = 8
BYTE_UNITS = {
    'b': 1,
    'k': 1024,
    'm': 1024 * 1024,
    'g': 1024 * 1024 * 1024
}

async def debug_shell():
    await embed(locals=locals(), globals=globals(), return_asyncio_coroutine=True, patch_stdout=True)

def parse_repository_tag(repo_name):
    parts = repo_name.rsplit('@', 1)
    if len(parts) == 2:
        return tuple(parts)
    parts = repo_name.rsplit(':', 1)
    if len(parts) == 2 and '/' not in parts[1]:
        return tuple(parts)
    return repo_name, None

def split_command(command):
    return shlex.split(command)

def get_raw_response_socket(client):
    if isinstance(client, httpx.AsyncClient):
        return client._transport._pool.connections[0]._connection._network_stream

    raise NotImplementedError

def convert_filters(f):
    if isinstance(f, dict):
        result = {}
        for k, v in iter(f.items()):
            if isinstance(v, bool):
                v = 'true' if v else 'false'
            if not isinstance(v, list):
                v = [v, ]
            result[k] = [
                str(item) if not isinstance(item, str) else item
                for item in v
            ]

        return json.dumps(result)

def parse_bytes(s):
    """
    https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/utils/utils.py#L402
    """

    if isinstance(s, (int, float,)):
        return s
    if len(s) == 0:
        return 0

    if s[-2:-1].isalpha() and s[-1].isalpha():
        if s[-1] == "b" or s[-1] == "B":
            s = s[:-1]
    units = BYTE_UNITS
    suffix = s[-1].lower()

    # Check if the variable is a string representation of an int
    # without a units part. Assuming that the units are bytes.
    if suffix.isdigit():
        digits_part = s
        suffix = 'b'
    else:
        digits_part = s[:-1]

    if suffix in units.keys() or suffix.isdigit():
        try:
            digits = float(digits_part)
        except ValueError as ve:
            raise DockerException(
                'Failed converting the string value for memory '
                f'({digits_part}) to an integer.'
            ) from ve

        # Reconvert to long for the final result
        s = int(digits * units[suffix])
    else:
        raise DockerException(
            f'The specified value for memory ({s}) should specify the units. '
            'The postfix should be one of the `b` `k` `m` `g` characters'
        )

    return s

'''
https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/utils/socket.py#L92
'''

async def next_frame_header(socket):
    """
    Returns the stream and size of the next frame of data waiting to be read
    from socket, according to the protocol defined here:

    https://docs.docker.com/engine/api/v1.24/#attach-to-a-container
    """

    data = await socket.read(STREAM_HEADER_SIZE_BYTES)
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
        if not result:
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

async def multiplexed_buffer_helper(buf):
    """A generator of multiplexed data blocks read from a buffered
    response."""

    buf_length = len(buf)
    walker = 0
    while True:
        if buf_length - walker < STREAM_HEADER_SIZE_BYTES:
            break
        header = buf[walker:walker + STREAM_HEADER_SIZE_BYTES]
        _, length = struct.unpack_from('>BxxxL', header)
        start = walker + STREAM_HEADER_SIZE_BYTES
        end = start + length
        walker = end
        yield buf[start:end]

async def get_results(res, is_tty):
    if is_tty:
        return res

    return b''.join([
        data async for data in multiplexed_buffer_helper(res)
    ])
