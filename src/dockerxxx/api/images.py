from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator, Field
from .generics import Response
from ..utils import convert_filters, parse_repository_tag
from ..transports import BaseTransport
from ..models import ImageSummary, ImageInspect

class ImageListParams(BaseModel):
    all: Optional[bool] = False
    filters: Optional[Dict[Any, Any] | str] = None
    shared_size: Optional[bool] = Field(False, alias='shared-size')
    digests: Optional[bool] = False

    @field_validator('filters')
    def convert_filters(cls, f):
        return convert_filters(f)

class Image(ImageInspect):
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

    async def remove(self, force: bool = False, noprune: bool = False):
        await self.transport.client.delete(
            f"/images/{self.id}",
            params={'force': force, 'noprune': noprune}
        )

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

    async def get(self, image: str | ImageSummary):
        if isinstance(image, str):
            image_id = image
        elif isinstance(image, ImageSummary):
            image_id = image.id[:12]
        else:
            raise NotImplementedError

        r = await self.transport.client.get(f"/images/{image_id}/json")
        return Image.model_validate(r.json())

    async def get_registry_data(self, **kwargs):
        raise NotImplementedError

    async def list(self, all: bool = False, filters: Dict[Any, Any] = None,
                   shared_size: bool = False, digests: bool = False) -> List[ImageSummary]:
        r = await self.transport.client.get(
            "/images/json",
            params=ImageListParams(all=all, filters=filters,
                                   shared_size=shared_size, digests=digests).model_dump()
        )
        return Response[ImageSummary](data=r.json()).data

    async def load(self, **kwargs):
        raise NotImplementedError

    async def prune(self, **kwargs):
        raise NotImplementedError

    async def _pull_stream(self, params, headers):
        async with self.transport.client.stream(
            "POST",
            "/images/create",
            params=params,
            headers=headers
        ) as r:
            async for chunk in r.aiter_text():
                yield chunk

    async def pull(self, repository: str, tag: str = None, stream: bool = False, auth_config: bool = None,
             decode: bool = False, platform: str = None, all_tags: bool = False):

        repository, image_tag = parse_repository_tag(repository)
        tag = tag or image_tag or 'latest'

        if all_tags:
            tag = None

        #registry, repo_name = auth.resolve_repository_name(repository)

        params = {
            'tag': tag,
            'fromImage': repository
        }
        headers = {}

        if platform:
            params['platform'] = platform

        if stream:
            return self._pull_stream(params, headers)

        return (await self.transport.client.post(
            "/images/create",
            params=params,
            headers=headers
        )).content

    async def push(self, **kwargs):
        raise NotImplementedError

    async def remove(self, **kwargs):
        raise NotImplementedError

    async def search(self, **kwargs):
        raise NotImplementedError
