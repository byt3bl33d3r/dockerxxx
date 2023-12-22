import httpx
import structlog
import asyncssh
import secrets
from dockerxxx.utils import debug_shell
from pydantic import ConfigDict, BaseModel, field_validator, AnyUrl, Field
from pydantic_core.core_schema import FieldValidationInfo

log = structlog.get_logger("dockerxxx")

class BaseTransport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: AnyUrl
    client: httpx.Client | httpx.AsyncClient | None = Field(None, validate_default=True)

class UnixSocketTransport(BaseTransport):
    @field_validator('client')
    def set_client(cls, v, info: FieldValidationInfo):
        transport = httpx.HTTPTransport(uds=info.data['url'].path, retries=3)
        return httpx.Client(transport=transport, base_url="http://docker",
                            event_hooks={'response': [lambda r: r.raise_for_status()]})

class AsyncUnixSocketTransport(BaseTransport):
    @field_validator('client')
    def set_client(cls, v, info: FieldValidationInfo):

        async def raise_on_4xx_5xx(response):
            if response.status_code != 101:
                response.raise_for_status()

        async def log_request(request):
            log.debug(f"-> {request.url}", method=request.method, body=request.content)

        async def log_response(response):
            log.debug(f"<- {response.url}", status=response.status_code, headers=dict(response.headers))

        transport = httpx.AsyncHTTPTransport(uds=info.data['url'].path, retries=3)
        return httpx.AsyncClient(transport=transport, base_url="http://docker",
                                 event_hooks={'request': [log_request], 'response': [raise_on_4xx_5xx, log_response]})

class AsyncSshTransport(BaseTransport):
    async def forward_socket(remote_host: str, remote_uds_path: str = "/var/run/docker.sock") -> str:
        options = asyncssh.SSHClientConnectionOptions(
            username="",
            password="",
            client_keys=[]
        )
        rand_uds_name = secrets.token_hex(nbytes=10)
        uds_path = f"/var/run/{rand_uds_name}.sock"
        conn = await asyncssh.connect("localhost", options=options)
        listener = await conn.forward_remote_path(remote_uds_path, uds_path)

        return uds_path

    @field_validator('client')
    def set_client(cls, v, info: FieldValidationInfo):
        transport = httpx.AsyncHTTPTransport(uds=info.data['url'].path)
        return httpx.AsyncClient(transport=transport, base_url="http://docker") 

class SshTransport:
    pass

class HttpTransport:
    pass

class AsyncHttpTransport:
    pass
