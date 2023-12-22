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
from pydantic import BaseModel, AnyUrl, field_validator, ValidationError, Field, ConfigDict
from pydantic.types import Path
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    docker_host: AnyUrl = "unix://var/run/docker.sock"
    docker_tls_verify: bool = True
    docker_cert_path: Path | None = None


class BaseDockerClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url : AnyUrl = "unix://var/run/docker.sock"
    version: str = "auto"
    timeout: int = 5
    tls: bool = True
    user_agent: str | None
    transport: BaseTransport | None = Field(None, validate_default=True)

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

class AsyncDockerClient(BaseDockerClient):
    '''
    https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/api/client.py
    '''

    @field_validator('transport')
    def set_transport(cls, v, info: FieldValidationInfo) -> AsyncUnixSocketTransport | AsyncSshTransport | AsyncHttpTransport:
        if info.data['base_url'].scheme == 'unix':
            return AsyncUnixSocketTransport(url=info.data['base_url'])

        raise NotImplementedError

    async def login(self):
        raise NotImplementedError

    async def df(self):
        raise NotImplementedError

    async def events(self):
        raise NotImplementedError

    async def ping(self):
        raise NotImplementedError

    async def info(self):
        r = await self.transport.client.get("/info")
        return SystemInfo.model_validate(r.json())

    async def daemon_version(self):
        r = await self.transport.client.get("/version")
        return SystemVersion.model_validate(r.json())

class DockerClient(BaseDockerClient):
    @field_validator('transport')
    def set_transport(cls, v, info: FieldValidationInfo) -> UnixSocketTransport | HttpTransport | SshTransport:
        if info.data['base_url'].scheme == 'unix':
            return UnixSocketTransport(url=info.data['base_url'])

        raise NotImplementedError

    def info(self):
        r = self.transport.client.get("/info")
        return SystemInfo.model_validate(r.json())
