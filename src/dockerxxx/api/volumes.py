import asyncio
from ..transports import BaseTransport
from ..models import Volume as VolumeResponse
from .generics import Response
from ..models import VolumeCreateOptions, VolumeListResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List

class VolumePruneResponse(BaseModel):
    volumes_deleted: List[str] = Field(alias="VolumesDeleted")
    space_reclaimed: int = Field(alias="SpaceReclaimed")

class Volume(VolumeResponse):
    model_config = ConfigDict(validate_assignment=True)

    transport: Optional[BaseTransport] = None

    async def reload(self) -> None:
        r = await self.transport.client.get(f"/volumes/{self.id}")
        inspect = VolumeResponse.model_validate(r.json())
        for k in inspect.model_fields:
            setattr(self, k, getattr(inspect, k))

    async def remove(self, force: bool = False) -> None:
        await self.transport.client.delete(
            f"/volumes/{self.id}",
            params={"force": force}
        )

class Volumes(BaseModel):
    transport: BaseTransport

    async def create(self, name: str, driver: str = None, 
                     driver_opts: Dict[str, str] = None, labels: Dict[str, str] = None) -> Volume:
        r = await self.transport.client.post(
            "/volumes",
            json=VolumeCreateOptions(
                name=name, driver=driver, 
                driver_opts=driver_opts, labels=labels
            ).model_dump(by_alias=True)
        )

        volume = VolumeResponse.model_validate(r.json())
        return await self.get(volume)

    async def list(self, filters: Dict[str, str] = None) -> List[Volume]:
        r = await self.transport.client.get(
            "/volumes",
            params={"filters": filters}
        )

        volumes = Response[VolumeListResponse](data=r.json()).data
        return await asyncio.gather(*[
            self.get(volume.id) for volume in volumes
        ])

    async def get(self, volume: str | VolumeResponse | VolumeListResponse) -> Volume:
        if isinstance(volume, str):
            volume_id = volume
        elif isinstance(volume, (VolumeResponse, VolumeListResponse)):
            volume_id = volume.id

        r = await self.transport.client.get(f"/volumes/{volume_id}")
        volume = Volume.model_validate(r.json())
        volume.transport = self.transport
        return volume

    async def prune(self, filters: Dict[str, str] = None) -> VolumePruneResponse:
        r = await self.transport.client.post(
            "/volumes/prune",
            params={"filters": filters}
        )

        return VolumePruneResponse.model_validate(r.json())
