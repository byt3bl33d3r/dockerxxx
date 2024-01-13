import pytest
from dockerxxx import AsyncDocker
from dockerxxx.models import SystemInfo, SystemVersion

@pytest.mark.asyncio(scope="session")
class TestClient:

    async def test_system_info(self, docker: AsyncDocker):
        info = await docker.info()
        assert isinstance(info, SystemInfo)

    async def test_system_version(self, docker: AsyncDocker):
        version = await docker.daemon_version()
        assert isinstance(version, SystemVersion)

    async def test_df(self, docker: AsyncDocker):
        df = await docker.df()
        assert len(df)

    async def test_ping(self, docker: AsyncDocker):
        pong = await docker.ping()
        assert pong == 'OK'
