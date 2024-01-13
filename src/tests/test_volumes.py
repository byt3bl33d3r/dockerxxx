import pytest
from dockerxxx import AsyncDocker

@pytest.mark.asyncio(scope="session")
class TestVolume:
    async def test_create_get(self, client: AsyncDocker):
        volume = await client.volumes.create(
            'dockerpytest_1',
            driver='local',
            labels={'labelkey': 'labelvalue'}
        )

        #self.tmp_volumes.append(volume.id)
        assert volume.id
        assert volume.name == 'dockerpytest_1'
        assert volume.labels == {'labelkey': 'labelvalue'}

        volume = await client.volumes.get(volume.id)
        assert volume.name == 'dockerpytest_1'

    async def test_list_remove(self, client: AsyncDocker):
        volume = await client.volumes.create('dockerpytest_1')
        #self.tmp_volumes.append(volume.id)
        assert volume in await client.volumes.list()
        assert volume in await client.volumes.list(filters={'name': 'dockerpytest_'})
        assert volume not in await client.volumes.list(filters={'name': 'foobar'})

        await volume.remove()
        assert volume not in await client.volumes.list()
