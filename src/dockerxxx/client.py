import asyncio
from .transports import (
    BaseTransport,
    UnixSocketTransport,
    HttpTransport,
    SshTransport,
    AsyncUnixSocketTransport,
    AsyncHttpTransport,
    AsyncSshTransport
)
from .api import Images, Containers
from .models import SystemInfo, SystemVersion
from .utils import convert_filters
from .errors import DockerException
from typing import Optional, Dict, Any
from pydantic import BaseModel, AnyUrl, field_validator, Field, ConfigDict
from pydantic.types import Path
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    docker_host: AnyUrl = "unix:///var/run/docker.sock"
    docker_tls_verify: bool = True
    docker_cert_path: Optional[Path] = None


class BaseDockerClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url : AnyUrl = "unix:///var/run/docker.sock"
    version: str = "auto"
    timeout: int = 5
    tls: bool = True
    user_agent: Optional[str] = None
    transport: Optional[BaseTransport] = Field(None, validate_default=True)

    @classmethod
    def from_env(cls, version: str = "auto", timeout: int = 5, user_agent: str = None):
        settings = EnvSettings()
        return cls(
            base_url=settings.docker_host,
            version=version,
            timeout=timeout,
            tls=settings.docker_tls_verify,
            user_agent=user_agent
        )

    @property
    def images(self):
        return Images(transport=self.transport)

    @property
    def containers(self):
        return Containers(transport=self.transport)

class EventStreamParams(BaseModel):
    since: Optional[str] = None
    until: Optional[str] = None
    filters: Optional[Dict[Any, Any] | str] = None

    @field_validator('filters')
    def convert_filters(cls, f):
        return convert_filters(f)

class AsyncDockerClient(BaseDockerClient):
    '''
    https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/api/client.py
    '''

    @field_validator('transport')
    def set_transport(cls, v, info: ValidationInfo) -> AsyncUnixSocketTransport | AsyncSshTransport | AsyncHttpTransport:
        if info.data['base_url'].scheme == 'unix':
            return AsyncUnixSocketTransport(url=info.data['base_url'])

        elif info.data['base_url'].scheme in ['ssh', 'unix+ssh', 'ssh+unix']:
            ssh_transport = AsyncSshTransport(url=info.data['base_url'])
            asyncio.create_task(ssh_transport.forward_socket())
            return AsyncUnixSocketTransport(url=ssh_transport.uds_url)

        elif info.data['base_url'].scheme in ['ssh+http', 'http+ssh']:
            raise NotImplementedError

        elif info.data['base_url'].scheme in ['http']:
            raise NotImplementedError

        raise DockerException(
            f"Protocol {info.data['base_url'].scheme} is not supported, "
            "supported protocols are: unix://, ssh://, http://, ssh+http://"
        )

    async def login(self):
        raise NotImplementedError

    async def df(self):
        r = await self.transport.client.get("/system/df")
        #return SystemDataUsageResponse.model_validate(r.json())
        return r.json()

    async def events(self, since: str = None, until: str = None, filters: Dict[Any, Any] = None):
        async with self.transport.client.stream(
            "GET", "/events",
            params=EventStreamParams(since=since, until=until, filters=filters).model_dump()
        ) as event_stream:
            async for event in event_stream.aiter_text():
                #yield SystemEventResponse.model_validate(r.json())
                yield event

    async def ping(self):
        return (await self.transport.client.get("/_ping")).text

    async def info(self):
        r = await self.transport.client.get("/info")
        return SystemInfo.model_validate(r.json())

    async def daemon_version(self):
        r = await self.transport.client.get("/version")
        return SystemVersion.model_validate(r.json())

class DockerClient(BaseDockerClient):
    @field_validator('transport')
    def set_transport(cls, v, info: ValidationInfo) -> UnixSocketTransport | HttpTransport | SshTransport:
        if info.data['base_url'].scheme == 'unix':
            return UnixSocketTransport(url=info.data['base_url'])

        raise NotImplementedError
