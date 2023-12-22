import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from .images import Image
from .exec import Exec, ExecCreateConfig, ExecStartConfig, ExecResults
from .generics import Response
from ..models import ContainerSummary, ContainerConfig, ContainerCreateResponse, ContainerWaitResponse
from ..transports import BaseTransport
from ..errors import ContainerError
from ..utils import split_command
from pydantic import field_validator, validator
from pydantic import BaseModel, Field, ConfigDict

class ContainerLogParams(BaseModel):
    stderr: bool
    stdout: bool
    timestamps: bool
    follow: bool
    tail: Optional[int | str] = 'all'
    since: Optional[datetime] = None
    until: Optional[datetime] = None

class ContainerListParams(BaseModel):
    filters: Optional[Dict[Any, Any] | str] = None
    limit: Optional[int] = -1
    all: Optional[bool] = False
    since: Optional[str] = None
    before: Optional[str] = None

    @validator('filters')
    def convert_filters(cls, f):
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

class Container(ContainerSummary):
    transport: Optional[BaseTransport] = Field(None)
    #model_config = ConfigDict(extra='allow')

    @field_validator('id')
    def shorten_id(cls, v):
        return v[:12]

    @field_validator('names')
    def shorten_names(cls, v):
        return [ name.strip('/') for name in v ]

    @field_validator('image_id')
    def shorten_image_id(cls, v):
        return v.split(':')[1][:12]

    async def attach(self, **kwargs):
        raise NotImplementedError

    async def attach_socket(self):
        raise NotImplementedError
    
    async def commit(self):
        raise NotImplementedError

    async def diff(self):
        raise NotImplementedError

    async def exec_run(self, cmd: str, stdout: bool = True, stderr: bool = True, stdin: bool = False, tty: bool = False,
                        privileged: bool = False, user: str = '', detach: bool = False, stream: bool = False,
                        socket: bool = False, environment: Dict[str, str] | List[str] = None, 
                        workdir: str = None, demux: bool = False) -> ExecResults:

        exec_session = Exec(transport=self.transport)

        resp = await exec_session.create(
            ExecCreateConfig(
                container=self.id,
                cmd=cmd,
                stdout=stdout, stderr=stderr, stdin=stdin, tty=tty,
                privileged=privileged, user=user, environment=environment,
                workdir=workdir
        ))

        output = await exec_session.start(
            ExecStartConfig(
                exec_id=resp['Id'],
                detach=detach, tty=tty, stream=stream, socket=socket,
                demux=demux
        ))

        inspection = await exec_session.inspect(resp['Id'])

        return ExecResults(
            exit_code=inspection['ExitCode'],
            output=output
        )

    async def export(self):
        raise NotImplementedError

    async def get_archive(self):
        raise NotImplementedError

    async def start(self):
        await self.transport.client.post(f"/containers/{self.id}/start")

    async def remove(self, v=False, link=False, force=False):
        await self.transport.client.delete(
            f"/containers/{self.id}",
            params={'force': force, 'link': link, 'v': v}
        )

    async def kill(self):
        raise NotImplementedError

    async def _logs_stream(self, container_log_params: ContainerLogParams):
        async with self.transport.client.stream(
            "GET",
            f"/containers/{self.id}/logs",
            params=container_log_params.model_dump()
        ) as r:
            async for chunk in r.aiter_bytes():
                yield chunk

    async def logs(self, stdout: bool = True, stderr: bool = True, stream: bool = False,
             timestamps: bool = False, tail: str | int = 'all', since: str = None, follow: bool = False,
             until: str = None):

        log_params = ContainerLogParams(
            stdout=stdout, stderr=stderr, 
            timestamps=timestamps, follow=follow,
            tail=tail, since=since, until=until
        )

        if not stream:
            return (await self.transport.client.get(
                f"/containers/{self.id}/logs",
                params=log_params.model_dump()
            )).content
        else:
            return self._logs_stream(log_params)

    async def top(self, ps_args: str = None):
        r = await self.transport.client.get(
            f'/containers/{self.id}/top',
            params={'ps_args': ps_args}
        )
        return r.json()

    async def wait(self, timeout: int = None, condition: str = None):
        r = await self.transport.client.post(
            f"/containers/{self.id}/wait",
            params={"condition": condition},
            timeout=timeout
        )

        return ContainerWaitResponse.model_validate(r.json())

class Containers(BaseModel):
    transport: BaseTransport

    async def run(self, image: str | Image, command=None, stdout=True, stderr=False, remove=False, **kwargs):
        output = None

        if isinstance(image, Image):
            image = image.id

        stream = kwargs.pop('stream', False)
        detach = kwargs.pop('detach', False)
        platform = kwargs.get('platform', None)

        if detach and remove:
            kwargs["auto_remove"] = True

        if kwargs.get('network') and kwargs.get('network_mode'):
            raise RuntimeError(
                'The options "network" and "network_mode" can not be used '
                'together.'
            )

        if kwargs.get('networking_config') and not kwargs.get('network'):
            raise RuntimeError(
                'The option "networking_config" can not be used '
                'without "network".'
            )

        try:
            container = await self.create(
                image=image, command=command,
                detach=detach, **kwargs
            )

            await container.start()

            if detach:
                return container

            output = await container.logs(
                stdout=stdout, stderr=stderr, stream=True, follow=True
            )

            exit_status = (await container.wait()).status_code
            if exit_status != 0:
                output = None
                if not kwargs.get('auto_remove'):
                    output = await container.logs(stdout=False, stderr=True)

            if exit_status != 0:
                raise ContainerError(
                    container, exit_status, command, image, output
                )

            return output if stream or output is None else b''.join(
                [line async for line in output]
            )

        finally:
            if remove: await container.remove()

    async def create(self, image: str | Image, command: str = None, **kwargs) -> Container:
        if isinstance(image, Image):
            image = image.id

        kwargs['image'] = image
        kwargs['cmd'] = split_command(command)

        r = await self.transport.client.post(
            "/containers/create",
            json=ContainerConfig.model_validate(kwargs).model_dump(by_alias=True)
        )

        container = ContainerCreateResponse.model_validate(r.json())
        return await self.get(container.id)

    async def get(self, container_id: str) -> Container:
        r = await self.transport.client.get(f"/containers/{container_id}/json")
        #print(Container.model_fields)
        return ( await self.list(all=True, filters={"id": container_id}) )[0]

    async def list(self, all: bool = False, before: str = None,
                   filters: Dict[Any, Any] = None, limit: int = -1, since: str = None,
                   sparse: bool = False, ignore_removed: bool = False) -> List[ContainerSummary]:

        r = await self.transport.client.get(
            "/containers/json", 
            params=ContainerListParams(all=all, before=before, filters=filters, limit=limit, since=since).model_dump()
        )

        containers = Response[Container](data=r.json()).data
        list(map(lambda c: setattr(c, 'transport', self.transport), containers))
        return containers

    async def prune(self):
        raise NotImplementedError
