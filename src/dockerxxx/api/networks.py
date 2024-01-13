import asyncio
from ..models import Network as NetworkResponse
from ..models import EndpointSettings, IPAM
from ..transports import BaseTransport
from .generics import Response
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any

class NetworkCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="Name")
    check_duplicate: Optional[bool] = Field(None, alias="CheckDuplicate")
    driver: Optional[str] = Field(None, alias="Driver")
    internal: Optional[bool]  = Field(None, alias="Internal")
    attachable: Optional[bool] = Field(None, alias="Attachable")
    ingress: Optional[bool] = Field(None, alias="Ingress")
    ipam: Optional[IPAM] = Field(None, alias="IPAM")
    enable_ipv6: Optional[bool] = Field(None, alias="EnableIPv6")
    options: Optional[Dict[str, str]] = Field(None, alias="Options")
    labels: Optional[Dict[str, str]] = Field(None, alias="Labels")

class NetworkCreateResponse(BaseModel):
    id: str = Field(alias="Id")
    warning: str = Field(alias="Warning")

class NetworkPruneResponse(BaseModel):
    networks_deleted: List[str] = Field(alias="NetworksDeleted")

class NetworkDisconnectRequest(BaseModel):
    container: str = Field(alias="Container")
    force: bool = Field(alias="Force")

class NetworkConnectRequest(BaseModel):
    container: str = Field(alias="Container")
    endpoint_config: EndpointSettings = Field(alias="EndpointConfig")

class Network(NetworkResponse):
    model_config = ConfigDict(validate_assignment=True)

    transport: Optional[BaseTransport] = None

    async def connect(self, container: str, aliases: List[str] = None, links: List[str] = None, 
                      ipv4_address: str = None, ipv6_address: str = None, link_local_ips: List[str] = None,
                      driver_opt: Dict[Any, Any] = None):
        container_id = container

        await self.transport.client.post(
            f"/networks/{self.id}/connect",
            json=NetworkConnectRequest(container=container_id).model_dump(by_alias=True)
        )

    async def disconnect(self, container: str, force: bool = False):
        container_id = container

        await self.transport.client.post(
            f"/networks/{self.id}/disconnect",
            json=NetworkDisconnectRequest(
                container=container_id, force=force
            ).model_dump(by_alias=True)
        )

    async def reload(self):
        r = await self.transport.client.get(f"/networks/{self.id}")
        inspect = NetworkResponse.model_validate(r.json())
        for k in inspect.model_fields:
            setattr(self, k, getattr(inspect, k))

    async def remove(self):
        await self.transport.client.delete(f"/networks/{self.id}")


class Networks(BaseModel):
    transport: BaseTransport

    async def create(self, name: str, driver = None, options = None, 
                     ipam = None, check_duplicate = None, internal = None, labels = None,
                     enable_ipv6 = None, attachable = None, scope = None, ingress = None) -> Network:

        r = await self.transport.client.post(
            "/networks",
            json=NetworkCreateRequest(
                name=name, driver=driver, options=options,
                ipam=ipam, check_duplicate=check_duplicate, internal=internal,
                labels=labels, enable_ipv6=enable_ipv6, attachable=attachable, 
                ingress=ingress
            ).model_dump(by_alias=True)
        )

        network = NetworkCreateResponse.model_validate(r.json())
        return await self.get(network)

    async def get(self, network: str | NetworkResponse | Network | NetworkCreateResponse):
        if isinstance(network, str):
            network_id = network
        elif isinstance(network, (NetworkResponse, NetworkCreateResponse, Network)):
            network_id = network.id

        r = await self.transport.client.get(f"/networks/{network_id}")
        network = Network.model_validate(r.json())
        network.transport = self.transport
        return network

    async def list(self, names: List[str] = None, ids: List[str] = None, 
                   filters: Dict[str, str] = None, greedy: bool = False):
        r = await self.transport.client.get("/networks")

        networks = Response[NetworkResponse](data=r.json()).data
        return await asyncio.gather(*[
            self.get(network.id) for network in networks
        ])

    async def prune(self, filters: None):
        r = await self.transport.client.post(
            "/networks/prune",
            params={"filters": filters}
        )

        return NetworkPruneResponse.model_validate(r.json())
