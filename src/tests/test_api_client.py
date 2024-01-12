import pytest
from dockerxxx import AsyncDocker
from dockerxxx.models import SystemInfo, SystemVersion

@pytest.mark.asyncio(scope="session")
async def test_api_client(docker: AsyncDocker):
    info = await docker.info()
    assert isinstance(info, SystemInfo)

    version = await docker.daemon_version()
    assert isinstance(version, SystemVersion)

    df = await docker.df()