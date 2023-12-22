from typing import List
from pydantic import BaseModel
from .generics import Response
from ..transports import BaseTransport
from ..models import ImageSummary

class Image(ImageSummary):
    """
    https://docker-py.readthedocs.io/en/stable/images.html#image-objects
    """

    transport: BaseTransport

    async def history(self, **kwargs):
        raise NotImplementedError

    async def reload(self, **kwargs):
        raise NotImplementedError

    async def save(self, **kwargs):
        raise NotImplementedError

    async def tag(self, **kwargs):
        raise NotImplementedError

class RegistryData(BaseModel):
    """
    https://docker-py.readthedocs.io/en/stable/images.html#registrydata-objects
    """

    id: str
    short_id: str

    async def has_platform(self, platform: str) -> bool:
        raise NotImplementedError

    async def pull(self, platform: str = None) -> Image:
        raise NotImplementedError

    async def reload(self) -> None:
        raise NotImplementedError

class Images(BaseModel):
    """
    https://docker-py.readthedocs.io/en/stable/images.html#module-docker.models.images
    """

    transport: BaseTransport

    async def build(self, **kwargs):
        raise NotImplementedError

    async def get(self, **kwargs):
        raise NotImplementedError

    async def get_registry_data(self, **kwargs):
        raise NotImplementedError

    async def list(self) -> List[ImageSummary]:
        r = await self.transport.client.get("/images/json")
        return Response[ImageSummary](data=r.json()).data

    async def load(self, **kwargs):
        raise NotImplementedError

    async def prune(self, **kwargs):
        raise NotImplementedError

    async def pull(self, **kwargs):
        raise NotImplementedError

    async def push(self, **kwargs):
        raise NotImplementedError

    async def remove(self, **kwargs):
        raise NotImplementedError

    async def search(self, **kwargs):
        raise NotImplementedError
