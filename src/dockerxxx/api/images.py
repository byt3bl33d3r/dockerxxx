import json
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator, Field
from .generics import Response
from ..utils import convert_filters, parse_repository_tag
from ..transports import BaseTransport
from ..models import ImageSummary, ImageInspect
from pydantic_core.core_schema import ValidationInfo

class ImageListParams(BaseModel):
    all: Optional[bool] = False
    only_ids: Optional[bool] = False
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

    transport: Optional[BaseTransport] = Field(None)
    name: Optional[str] = Field(None, validate_default=True)

    @field_validator('id')
    def shorten_id(cls, v):
        return v.split(':')[1][:12]

    @field_validator('name')
    def create_name(cls, v, info: ValidationInfo):
        if info.data['repo_tags']:
            return info.data['repo_tags'][0].split(':')[0]

        if info.data['repo_digests']:
            return info.data['repo_digests'][0].split('@')[0]

        return None

    async def history(self, **kwargs):
        raise NotImplementedError

    async def reload(self, **kwargs):
        raise NotImplementedError

    async def save(self, **kwargs):
        raise NotImplementedError

    async def tag(self, name: str, repo: str = None, tag: str = None, force: bool = False):
        r = await self.transport.client.post(
            f"/images/{self.id}/tag",
            params={
                "repo": repo,
                "tag": tag,
                "force": int(force)
            }
        )

        return r.status_code == 201

    async def remove(self, force: bool = False, noprune: bool = False):
        await self.transport.client.delete(
            f"/images/{self.id}",
            params={'force': force, 'noprune': noprune}
        )

    def __eq__(self, other):
        if isinstance(other, str):
            return (self.id == other) or (self.id == other[:12])
        elif isinstance(other, Image) or isinstance(other, ImageInspect):
            return other.id == self.id

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

    async def get(self, image: str | ImageSummary):
        if isinstance(image, str):
            image_id = image
        elif isinstance(image, ImageSummary):
            image_id = image.id[:12]
        else:
            raise NotImplementedError

        r = await self.transport.client.get(f"/images/{image_id}/json")
        image = Image.model_validate(r.json())
        image.transport = self.transport
        return image

    async def get_registry_data(self, **kwargs):
        raise NotImplementedError

    async def list(self, name: str = None, all: bool = False, filters: Dict[Any, Any] = None,
                   shared_size: bool = False, digests: bool = False, quiet: bool = False) -> List[Image]:
        """
        https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/api/image.py#L59C33-L59C38
        """

        if name:
            if filters:
                filters['reference'] = name
            else:
                filters = {'reference': name}

        r = await self.transport.client.get(
            "/images/json",
            params=ImageListParams(
                all=all, filters=filters, only_ids=quiet,
                shared_size=shared_size, digests=digests
            ).model_dump()
        )

        images = Response[ImageSummary](data=r.json()).data
        return await asyncio.gather(*[
            self.get(image.id) for image in images
        ])

    async def load(self, **kwargs):
        raise NotImplementedError

    async def prune(self, **kwargs):
        raise NotImplementedError

    async def _pull_stream(self, params, headers):
        async with self.transport.client.stream(
            "POST",
            "/images/create",
            params=params,
            headers=headers,
            timeout=None
        ) as r:
            async for chunk in r.aiter_lines():
                yield json.loads(chunk)

    async def pull(self, repository: str, tag: str = None, auth_config: bool = None,
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

        pull_logs = [log async for log in self._pull_stream(params, headers)]

        if not all_tags:
            sep = '@' if tag.startswith('sha256:') else ':'
            return await self.get(f'{repository}{sep}{tag}')

        return await self.list(filters={'reference': repository})

    async def push(self, **kwargs):
        raise NotImplementedError

    async def remove(self, **kwargs):
        raise NotImplementedError

    async def search(self, **kwargs):
        raise NotImplementedError
