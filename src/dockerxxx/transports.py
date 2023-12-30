import httpx
import structlog
import asyncssh
import secrets
from typing import Optional
from pydantic import ConfigDict, BaseModel, field_validator, model_validator, AnyUrl, Field
from pydantic_core.core_schema import ValidationInfo

def no_op_processor(logger, method_name, event_dict):
    raise structlog.DropEvent
    #return None  # Discard all logs

structlog.configure(processors=[no_op_processor])
log = structlog.get_logger()

async def raise_on_4xx_5xx(response):
    if response.status_code != 101:
        response.raise_for_status()

async def log_request(request):
    await log.adebug(f"-> {request.url}", method=request.method, body=request.content)

async def log_response(response):
    await log.adebug(f"<- {response.url}", status=response.status_code, headers=dict(response.headers))


class BaseTransport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: AnyUrl
    tls_verify: Optional[bool] = Field(True)
    client: Optional[httpx.Client | httpx.AsyncClient] = Field(None, validate_default=True)


class AsyncUnixSocketTransport(BaseTransport):
    @field_validator('client')
    def set_client(cls, v, info: ValidationInfo):
        log.debug("creating uds client", url=str(info.data['url'].path))
        transport = httpx.AsyncHTTPTransport(uds=info.data['url'].path, retries=3)
        return httpx.AsyncClient(transport=transport,
                                 base_url="http://docker",
                                 event_hooks={
                                    'request': [log_request],
                                    'response': [raise_on_4xx_5xx, log_response]
                                })


class AsyncSshTransport(BaseTransport):
    uds_url: AnyUrl = AnyUrl(f"unix:///tmp/dockerxxx-{secrets.token_hex(nbytes=6)}.sock")

    async def forward_socket(self, remote_uds_path: str = "/var/run/docker.sock") -> str:
        options = asyncssh.SSHClientConnectionOptions(
            username=self.url.username,
            password=self.url.password,
            known_hosts=None, # we should be able to turn this on via the URL
            client_keys=[]
        )

        await log.adebug("setting up ssh uds forwarding", local_path=self.uds_url.path, remote_path=remote_uds_path, url=str(self.url))

        conn = await asyncssh.connect(host=self.url.host, port=self.url.port, options=options)
        listener = await conn.forward_local_path(
            listen_path=self.uds_url.path,
            dest_path=remote_uds_path
        )


class AsyncHttpTransport(BaseTransport):
    @field_validator('client')
    def set_client(cls, v, info: ValidationInfo):
        scheme = info.data['url'].scheme
        netloc = (
            info.data['url'].host 
            if not info.data['url'].port
            else f"{info.data['url'].host}:{info.data['url'].port}"
        )

        log.debug(f"creating {scheme} client", url=str(info.data['url']))
        transport = httpx.AsyncHTTPTransport(retries=3, verify=info.data['tls_verify'])
        return httpx.AsyncClient(transport=transport,
                                 base_url=f"{scheme}://{netloc}",
                                 event_hooks={
                                    'request': [log_request],
                                    'response': [raise_on_4xx_5xx, log_response]
                                })


class SshTransport(BaseTransport):
    pass


class UnixSocketTransport(BaseTransport):
    pass


class HttpTransport(BaseTransport):
    pass
