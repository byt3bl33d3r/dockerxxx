import pytest

@pytest.mark.asyncio(scope="session")
async def test_images(docker):
    await docker.images.list()
