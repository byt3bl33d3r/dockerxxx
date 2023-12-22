import httpx
import structlog
import asyncssh
import secrets
from typing import Optional
from pydantic import ConfigDict, BaseModel, field_validator, AnyUrl, Field, FilePath
from pydantic_core.core_schema import ValidationInfo

log = structlog.get_logger("dockerxxx")

class BaseTransport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: AnyUrl
    client: Optional[httpx.Client | httpx.AsyncClient] = Field(None, validate_default=True)

class UnixSocketTransport(BaseTransport):
    @field_validator('client')
    def set_client(cls, v, info: ValidationInfo):
        transport = httpx.HTTPTransport(uds=info.data['url'].path, retries=3)
        return httpx.Client(transport=transport, base_url="http://docker",
                            event_hooks={'response': [lambda r: r.raise_for_status()]})

class AsyncUnixSocketTransport(BaseTransport):
    @field_validator('client')
    def set_client(cls, v, info: ValidationInfo):

        async def raise_on_4xx_5xx(response):
            if response.status_code != 101:
                response.raise_for_status()

        async def log_request(request):
            log.debug(f"-> {request.url}", method=request.method, body=request.content)

        async def log_response(response):
            log.debug(f"<- {response.url}", status=response.status_code, headers=dict(response.headers))

        log.debug("creating uds http client", url=str(info.data['url'].path))
        transport = httpx.AsyncHTTPTransport(uds=info.data['url'].path, retries=3)
        return httpx.AsyncClient(transport=transport, base_url="http://docker",
                                 event_hooks={'request': [log_request], 'response': [raise_on_4xx_5xx, log_response]})

class AsyncSshTransport(BaseTransport):
    uds_url: AnyUrl = AnyUrl(f"unix:///tmp/dockerxxx-{secrets.token_hex(nbytes=6)}.sock")

    async def forward_socket(self, remote_uds_path: str = "/var/run/docker.sock") -> str:
        options = asyncssh.SSHClientConnectionOptions(
            username=self.url.username,
            password=self.url.password,
            known_hosts=None,
            client_keys=[]
        )
        log.debug("setting up ssh uds forwarding", local_path=self.uds_url.path, remote_path=remote_uds_path, url=str(self.url))

        conn = await asyncssh.connect(host=self.url.host, port=self.url.port, options=options)
        listener = await conn.forward_local_path(
            listen_path=self.uds_url.path,
            dest_path=remote_uds_path
        )

class SshTransport:
    pass

class HttpTransport:
    pass

class AsyncHttpTransport:
    pass
