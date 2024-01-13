#import pytest
import pytest_asyncio
from dockerxxx import AsyncDocker
#from .test_containers import TestContainer

@pytest_asyncio.fixture(scope="session")
async def docker():
    return await AsyncDocker.from_env()

@pytest_asyncio.fixture(scope="session")
async def client(docker):
    yield docker

'''
@pytest_asyncio.fixture(scope="session", autouse=True)
async def teardown(docker: AsyncDocker):
    yield
    for c_id in TestContainer.tmp_containers:
        c = await docker.containers.get(c_id)
        await c.stop()
        await c.remove()
'''