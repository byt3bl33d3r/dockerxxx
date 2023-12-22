import pytest_asyncio
from dockerxxx.client import AsyncDockerClient

@pytest_asyncio.fixture(scope="session")
async def docker():
    return AsyncDockerClient.from_env()
