import pytest

@pytest.mark.asyncio(scope="session")
async def test_containers(docker):
    await docker.containers.list()
