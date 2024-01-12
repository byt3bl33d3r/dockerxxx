import pytest
from typing import List
from dockerxxx.api.containers import Container
from dockerxxx.models import ContainerSummary
from dockerxxx import AsyncDocker

@pytest.mark.asyncio(scope="session")
class TestContainer:
    tmp_containers: List[Container]

    async def test_list(self, docker: AsyncDocker):
        container_id = (await docker.containers.run(
            "alpine", "sleep 300", detach=True)).id

        #self.tmp_containers.append(container_id)

        containers = await docker.containers.list(filters={'id': container_id})

        assert len(containers) == 1

        container = containers[0]
        assert isinstance(container, Container)

        assert container.config.image == 'alpine'
        assert container.state.status.value == 'running'
        assert container.image == await docker.images.get('alpine')

        await container.kill()
        await container.remove()

        assert container_id not in [c.id for c in await docker.containers.list(all=True)]

    async def test_run_detach(self, docker: AsyncDocker):
        container = await docker.containers.run('alpine', 'sleep 300', detach=True)
        assert isinstance(container, Container)
        assert container.config.image == 'alpine'
        assert container.config.cmd == ['sleep', '300']

    async def test_run(self, docker: AsyncDocker):
        assert (
            await docker.containers.run(
                'alpine', 'echo hello world', remove=True
        )) == b'hello world\n'

    async def test_run_with_auto_remove(self, docker: AsyncDocker):
        out = await docker.containers.run(
            # sleep(2) to allow any communication with the container
            # before it gets removed by the host.
            'alpine', 'sh -c "echo hello && sleep 2"', auto_remove=True
        )
        assert out == b'hello\n'

        #cs = await docker.containers.list(all=True, filters={'id': out.id})
        #assert len(cs) == 0

    async def test_get(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sleep 300", detach=True)
        #self.tmp_containers.append(container.id)
        assert (await docker.containers.get(container.id)).config.image == "alpine"

    async def test_remove(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "echo hello", detach=True)
        #self.tmp_containers.append(container.id)
        assert container.id in [c.id[:12] for c in await docker.containers.list(all=True)]
        await container.wait()
        await container.remove()
        containers = await docker.containers.list(all=True)
        assert container.id not in [c.id[:12] for c in containers]

    async def test_wait(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sh -c 'exit 0'", detach=True)
        #self.tmp_containers.append(container.id)
        assert (await container.wait()).status_code == 0
        container = await docker.containers.run("alpine", "sh -c 'exit 1'", detach=True)
        #self.tmp_containers.append(container.id)
        assert (await container.wait()).status_code == 1

    async def test_top(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sleep 60", detach=True)
        #self.tmp_containers.append(container.id)
        top = await container.top()
        assert len(top['Processes']) == 1
        assert 'sleep 60' in top['Processes'][0]

    async def test_stop(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "top", detach=True)
        #self.tmp_containers.append(container.id)
        assert container.state.status.value in ("running", "created")
        await container.stop(timeout=2)
        await container.reload()
        assert container.state.status.value == "exited"

    async def test_stats(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sleep 100", detach=True)
        #self.tmp_containers.append(container.id)
        stats = await container.stats(stream=False)
        for key in ['read', 'networks', 'precpu_stats', 'cpu_stats',
                    'memory_stats', 'blkio_stats']:
            assert key in stats

    async def test_remove(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "echo hello", detach=True)
        #self.tmp_containers.append(container.id)
        assert container.id in [c.id for c in await docker.containers.list(all=True)]
        await container.wait()
        await container.remove()
        containers = await docker.containers.list(all=True)
        assert container.id not in [c.id for c in containers]

    async def test_rename(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "echo hello", name="test1",
                                          detach=True)
        #self.tmp_containers.append(container.id)
        assert container.name == "test1"
        await container.rename("test2")
        await container.reload()
        assert container.name == "test2"
