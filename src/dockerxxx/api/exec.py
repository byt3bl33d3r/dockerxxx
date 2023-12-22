from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import struct
from ..utils import split_command
from ..transports import BaseTransport
from ..utils import get_raw_response_socket, frames_iter

class ExecResults(BaseModel):
    exit_code: int
    output: str

class ExecCreateConfig(BaseModel):
    Container: str = Field(alias='container')
    Cmd: str | List[str] = Field(alias='cmd')
    AttachStdout: bool = Field(True, alias='stdout')
    AttachStderr: bool = Field(True, alias='stderr')
    AttachStdin: bool = Field(False, alias='stdin')
    Tty: bool = Field(False, alias='tty')
    Privileged: bool = Field(False, alias='privileged')
    User: str = Field('', alias='user')
    Env: Optional[Dict[str, str] | List[str]] = Field(None, alias='environment')

    #ConsoleSize: Optional[List[int]] = Field(None, alias='console_size')
    WorkingDir: Optional[str] = Field(None, alias='workdir')
    detachKeys: str = Field(None)

    @validator('Cmd')
    def string_cmd_to_list(cls, v):
        if isinstance(v, str):
            return split_command(v)
        return v

class ExecStartConfig(BaseModel):
    ExecId: str = Field(alias="exec_id")
    Detach: bool = Field(False, alias='detach')
    Tty: bool = Field(False, alias='tty')
    #ConsoleSize: Optional[List[int]] = Field(None, alias='console_size')
    Stream: bool = Field(False, alias='stream')
    Socket: bool = Field(False, alias='socket')
    Demux: bool = Field(False, alias='demux')


class Exec(BaseModel):
    """
    https://github.com/docker/docker-py/blob/main/docker/api/exec_api.py
    """

    transport: BaseTransport

    async def create(self, exec_create_config: ExecCreateConfig):
        return (await self.transport.client.post(
            f'/containers/{exec_create_config.Container}/exec',
            json=exec_create_config.model_dump(exclude=['Container', 'detachKeys'])
        )).json()

    async def start(self, exec_start_config: ExecStartConfig):
        output = b''

        headers = {} if exec_start_config.Detach else {
            'Connection': 'Upgrade',
            'Upgrade': 'tcp'
        }

        async with self.transport.client.stream("POST", f"/exec/{exec_start_config.ExecId}/start",
            headers=headers,
            json=exec_start_config.model_dump(include=['Tty', 'Detach']),
        ) as r:

            if exec_start_config.Detach:
                return (await r.aread())

            if exec_start_config.Socket:
                raise NotImplementedError

            raw_sock = get_raw_response_socket(self.transport.client)
            async for frame in await frames_iter(raw_sock, exec_start_config.Tty):
                stream, result = frame
                output += result

        return output

    async def inspect(self, exec_id: str | Dict[Any, Any]):
        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')

        return (await self.transport.client.get(f"/exec/{exec_id}/json")).json()

    async def resize(self, exec_id: str):
        raise NotImplementedError
