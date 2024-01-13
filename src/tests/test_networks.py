import pytest
from typing import List
from . import helpers
from dockerxxx import AsyncDocker

@pytest.mark.asyncio(scope="session")
class TestNetworks:
    tmp_networks: List[str]

    async def test_create(self, client: AsyncDocker):
        name = helpers.random_name()
        network = await client.networks.create(name, labels={'foo': 'bar'})
        #self.tmp_networks.append(network.id)
        assert network.name == name
        assert network.labels['foo'] == "bar"

    async def test_get(self, client: AsyncDocker):
        name = helpers.random_name()
        network_id = (await client.networks.create(name)).id
        #self.tmp_networks.append(network_id)
        network = await client.networks.get(network_id)
        assert network.name == name

    async def test_list_remove(self, client: AsyncDocker):
        name = helpers.random_name()
        network = await client.networks.create(name)
        #self.tmp_networks.append(network.id)
        assert network.id in [n.id for n in await client.networks.list()]
        assert network.id not in [
            n.id for n in
            await client.networks.list(ids=["fdhjklfdfdshjkfds"])
        ]
        assert network.id in [
            n.id for n in
            await client.networks.list(ids=[network.id])
        ]
        assert network.id not in [
            n.id for n in
            await client.networks.list(names=["fdshjklfdsjhkl"])
        ]
        assert network.id in [
            n.id for n in
            await client.networks.list(names=[name])
        ]
        await network.remove()
        assert network.id not in [n.id for n in await client.networks.list()]

    async def test_connect_disconnect(self, client: AsyncDocker):
        network = await client.networks.create(helpers.random_name())
        #self.tmp_networks.append(network.id)
        container = await client.containers.create("alpine", "sleep 300")
        #self.tmp_containers.append(container.id)
        assert network.containers == []
        await network.connect(container)
        await container.start()
        assert (await client.networks.get(network.id)).containers == [container]
        network_containers = [
            c
            for net in await client.networks.list(ids=[network.id], greedy=True)
            for c in net.containers
        ]
        assert network_containers == [container]
        await network.disconnect(container)
        assert network.containers == []
        assert (await client.networks.get(network.id)).containers == []
