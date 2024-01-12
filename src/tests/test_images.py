import pytest
from dockerxxx.api.images import Image
from dockerxxx import AsyncDocker

def get_ids(images):
    return [i.id for i in images]

@pytest.mark.asyncio(scope="session")
class TestImage:
    async def test_pull(self, docker: AsyncDocker):
        image = await docker.images.pull('alpine:latest')
        assert isinstance(image, Image)
        assert 'alpine:latest' in image.repo_tags

    async def test_pull_with_tag(self, docker: AsyncDocker):
        image = await docker.images.pull('alpine', tag='3.10')
        assert isinstance(image, Image)
        assert 'alpine:3.10' in image.repo_tags

    async def test_pull_with_sha(self, docker: AsyncDocker):
        image_ref = (
            'hello-world@sha256:083de497cff944f969d8499ab94f07134c50bcf5e6b95'
            '59b27182d3fa80ce3f7'
        )
        image = await docker.images.pull(image_ref)
        assert isinstance(image, Image)
        assert image_ref in image.repo_digests

    async def test_pull_multiple(self, docker: AsyncDocker):
        images = await docker.images.pull('hello-world', all_tags=True)
        assert len(images) >= 1
        assert any('hello-world:latest' in img.repo_tags for img in images)

    async def test_list(self, docker: AsyncDocker):
        image = await docker.images.pull('alpine:latest')
        images = await docker.images.list()
        assert all(map(lambda i: isinstance(i, Image), images))
        assert image.id in get_ids(images)

    async def test_list_with_repository(self, docker: AsyncDocker):
        image = await docker.images.pull('alpine:latest')
        assert image.id in get_ids(await docker.images.list('alpine'))
        assert image.id in get_ids(await docker.images.list('alpine:latest'))

    async def test_pull_with_tag(self, docker: AsyncDocker):
        image = await docker.images.pull('alpine', tag='3.10')
        assert 'alpine:3.10' in image.repo_tags

    async def test_pull_with_sha(self, docker: AsyncDocker):
        image_ref = (
            'hello-world@sha256:083de497cff944f969d8499ab94f07134c50bcf5e6b95'
            '59b27182d3fa80ce3f7'
        )
        image = await docker.images.pull(image_ref)
        assert image_ref in image.repo_digests

    async def test_tag_and_remove(self, docker: AsyncDocker):
        repo = 'dockersdk.tests.images.test_tag'
        tag = 'some-tag'
        identifier = f'{repo}:{tag}'

        image: Image = await docker.images.pull('alpine:latest')

        result = await image.tag(repo, tag)
        assert result is True
        #self.tmp_imgs.append(identifier)
        assert image.id in get_ids(await docker.images.list(repo))
        assert image.id in get_ids(await docker.images.list(identifier))

        await docker.images.remove(identifier)
        assert image.id not in get_ids(await docker.images.list(repo))
        assert image.id not in get_ids(await docker.images.list(identifier))

        assert image.id in get_ids(await docker.images.list('alpine:latest'))
