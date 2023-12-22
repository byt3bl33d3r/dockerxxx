import pytest

@pytest.mark.asyncio(scope="session")
async def test_api_client(docker):
    await docker.info()
    await docker.daemon_version()
