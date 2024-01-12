import pytest_asyncio
from dockerxxx import AsyncDocker

@pytest_asyncio.fixture(scope="session")
async def docker():
    return await AsyncDocker.from_env()
