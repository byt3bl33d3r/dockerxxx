from typing import List, Optional, Dict, Any
from datetime import datetime
from .images import Image
from .exec import Exec, ExecCreateConfig, ExecStartConfig, ExecResults
from .generics import Response
from ..models import (
    ContainerSummary, ContainerConfig, 
    ContainerCreateResponse, ContainerWaitResponse, 
    ContainerState, GraphDriverData, HostConfig,
    NetworkSettings, MountPoint
)
from ..transports import BaseTransport
from ..errors import ContainerError
from ..utils import split_command, convert_filters, get_raw_response_socket, get_results
from pydantic import field_validator
from pydantic import BaseModel, Field

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

    @field_validator('filters')
    def convert_filters(cls, f):
        return convert_filters(f)

class ContainerAttachParams(BaseModel):
    stdin: int = 0
    stdout: int = 1
    stderr: int = 1
    stream: int = 0
    logs: int = 0

class ContainerInspectResponse(BaseModel):
    id: str = Field(alias='Id', description='The ID of this container')
    created: str = Field(alias='Created', description='When the container was created')
    path: str = Field(alias='Path')
    args: List[str] = Field(alias='Args')
    state: Optional[ContainerState] = Field(None, alias='State', description='Containers running state')
    image: str = Field(
        alias='Image',
        description='The ID of the image that this container was created from',
    )
    resolve_conf_path: str = Field(alias='ResolvConfPath')
    hostname_path: str = Field(alias='HostnamePath')
    hosts_path: str = Field(alias='HostsPath')
    log_path: str = Field(alias='LogPath')
    name: str = Field(alias='Name')
    restart_count: int = Field(alias='RestartCount')
    driver: str = Field(alias='Driver')
    platform: str = Field(alias='Platform')
    mount_label: str = Field(alias='MountLabel')
    process_label: str = Field(alias='ProcessLabel')
    app_armor_profile: str = Field(alias='AppArmorProfile')
    exec_ids: Optional[List[str]] = Field(None, alias='ExecIDs')
    host_config: Optional[HostConfig] = Field(None, alias='HostConfig')
    graph_driver: Optional[GraphDriverData] = Field(None, alias='GraphDriver')
    size_rw: Optional[int] = Field(None, alias='SizeRW')
    size_root_fs: Optional[int] = Field(None, alias='SizeRootFs')
    mounts: Optional[List[MountPoint]] = Field(None, alias='Mounts')
    config: Optional[ContainerConfig] = Field(None, alias='Config')
    network_settings: Optional[NetworkSettings] = Field(None, alias='NetworkSettings')

class Container(ContainerInspectResponse):
    transport: Optional[BaseTransport] = Field(None)
    #model_config = ConfigDict(extra='allow')

    @field_validator('id')
    def shorten_id(cls, v):
        return v[:12]

    #@field_validator('names')
    #def shorten_names(cls, v):
    #    return [ name.strip('/') for name in v ]

    @field_validator('image')
    def shorten_image_id(cls, v):
        return v.split(':')[1][:12]

    async def attach_socket(self, stdin: bool = False, stdout: bool = True, 
                            stderr: bool = True, stream: bool = True):

        req = self.transport.client.build_request(
            "POST",
            f"/containers/{self.id}/attach",
            params=ContainerAttachParams(stdin=stdin, stdout=stdout, stderr=stderr, stream=stream).model_dump(),
            headers={
                'Connection': 'Upgrade',
                'Upgrade': 'tcp'
            }
        )

        r = await self.transport.client.send(req, stream=True)
        return r, get_raw_response_socket(self.transport.client)

    async def attach(self, stdout: bool = True, stderr: bool = True,
               stream: bool = False, logs: bool = False, demux: bool = False):
        raise NotImplementedError

    async def commit(self):
        raise NotImplementedError

    async def inspect(self):
        r = await self.transport.client.get(f"/containers/{self.id}/json")
        return ContainerInspectResponse.model_validate(r.json())

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

    async def stop(self):
        await self.transport.client.post(f"/containers/{self.id}/stop")

    async def remove(self, v: bool = False, link: bool = False, force: bool = False):
        await self.transport.client.delete(
            f"/containers/{self.id}",
            params={'force': force, 'link': link, 'v': v}
        )

    async def kill(self, signal: str | int = 'SIGKILL'):
        await self.transport.client.post(
            f"/containers/{self.id}/kill",
            params={'signal': signal}
        )

    async def _logs_stream(self, container_log_params: ContainerLogParams):
        async with self.transport.client.stream(
            "GET",
            f"/containers/{self.id}/logs",
            params=container_log_params.model_dump()
        ) as r:
            # if self.config.tty:
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

        if stream:
            return self._logs_stream(log_params)

        r = await self.transport.client.get(
            f"/containers/{self.id}/logs",
            params=log_params.model_dump()
        )

        return await get_results(r.content, self.config.tty)

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
        # https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/types/containers.py#L680

        if isinstance(image, Image):
            image = image.id

        labels = kwargs.get('labels')
        #ports = kwargs.get('ports')
        entrypoint = kwargs.get('entrypoint')
        detach = kwargs.get('detach')
        open_stdin = kwargs.get('open_stdin') or kwargs.get('stdin_open')

        if detach:
            kwargs['attach_stdout'] = False
            kwargs['attach_stderr'] = False

        if not detach and open_stdin:
            kwargs['attach_stdin'] = True
            kwargs['stdin_once'] = True

        if isinstance(labels, list):
            labels = {lbl: '' for lbl in labels}

        if isinstance(entrypoint, str):
            kwargs['entrypoint'] = split_command(entrypoint)

        kwargs['image'] = image
        kwargs['cmd'] = split_command(command)

        r = await self.transport.client.post(
            "/containers/create",
            json=ContainerConfig.model_validate(kwargs).model_dump(by_alias=True)
        )

        container = ContainerCreateResponse.model_validate(r.json())
        return await self.get(container.id[:12])

    async def get(self, container_id: str) -> Container:
        r = await self.transport.client.get(f"/containers/{container_id}/json")
        container = Container.model_validate(r.json())
        container.transport =  self.transport
        return container

    async def list(self, all: bool = False, before: str = None,
                   filters: Dict[Any, Any] = None, limit: int = -1, since: str = None,
                   sparse: bool = False, ignore_removed: bool = False) -> List[ContainerSummary]:

        r = await self.transport.client.get(
            "/containers/json", 
            params=ContainerListParams(all=all, before=before, filters=filters, limit=limit, since=since).model_dump()
        )

        containers = Response[ContainerSummary](data=r.json()).data
        return containers

    async def prune(self):
        raise NotImplementedError
