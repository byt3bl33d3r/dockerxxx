import pytest
import dockerxxx
from typing import List
from dockerxxx.api.containers import Container
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
        assert container.status == 'running'
        assert container.image == await docker.images.get('alpine')

        await container.kill()
        await container.remove()

        assert container_id not in [c.id for c in await docker.containers.list(all=True)]

    async def test_list_sparse(self, docker: AsyncDocker):
        container_id = (await docker.containers.run(
            "alpine", "sleep 300", detach=True)).id
        #self.tmp_containers.append(container_id)
        containers = [c for c in await docker.containers.list(sparse=True) if c.id ==
                      container_id]
        assert len(containers) == 1

        container = containers[0]
        assert container.config.image == 'alpine'
        assert container.status == 'running'
        assert container.image == await docker.images.get('alpine')
        with pytest.raises(dockerxxx.errors.DockerException):
            _ = container.config.labels

        await container.kill()
        await container.remove()
        assert container_id not in [c.id for c in await docker.containers.list()]

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

    async def test_run_with_streamed_logs(self, docker: AsyncDocker):
        out = await docker.containers.run(
            'alpine', 'sh -c "echo hello && echo world"', stream=True
        )
        logs = [ l async for l in out ]
        assert logs[0] == b'hello\n'
        assert logs[1] == b'world\n'

    async def test_run_with_auto_remove_error(self, docker: AsyncDocker):
        with pytest.raises(dockerxxx.errors.ContainerError) as e:
            await docker.containers.run(
                # sleep(2) to allow any communication with the container
                # before it gets removed by the host.
                'alpine', 'sh -c ">&2 echo error && sleep 2 && exit 1"',
                auto_remove=True
            )
        assert e.value.exit_status == 1
        assert e.value.stderr is None


    async def test_run_with_error(self, docker: AsyncDocker):
        with pytest.raises(dockerxxx.errors.ContainerError) as cm:
            await docker.containers.run("alpine", "cat /test", remove=True)
        assert cm.value.exit_status == 1
        assert "cat /test" in cm.exconly()
        assert "alpine" in cm.exconly()
        assert "No such file or directory" in cm.exconly()

    async def test_run_with_image_that_does_not_exist(self, docker: AsyncDocker):
        with pytest.raises(dockerxxx.errors.ImageNotFound):
            await docker.containers.run("dockerpytest_does_not_exist")

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
        assert container.status in ("running", "created")
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

    async def test_restart(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sleep 100", detach=True)
        #self.tmp_containers.append(container.id)
        first_started_at = container.state.started_at
        await container.restart()
        await container.reload()
        second_started_at = container.state.started_at
        assert first_started_at != second_started_at

    async def test_start(self, docker: AsyncDocker):
        container = await docker.containers.create("alpine", "sleep 50", detach=True)
        #self.tmp_containers.append(container.id)
        assert container.status == "created"
        assert not container.state.running
        await container.start()
        await container.reload()
        assert container.state.running
        assert container.status == "running"

    async def test_update(self, docker: AsyncDocker):
        container = await docker.containers.run(
            "alpine", "sleep 60", detach=True, cpu_shares=2
        )
        #self.tmp_containers.append(container.id)
        assert container.host_config.cpu_shares == 2
        await container.update(cpu_shares=3)
        await container.reload()
        assert container.host_config.cpu_shares == 3

    async def test_kill(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sleep 300", detach=True)
        #self.tmp_containers.append(container.id)
        while container.status != 'running':
            await container.reload()
        assert container.status == 'running'
        await container.kill()
        await container.reload()
        assert container.status == 'exited'

    async def test_pause(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "sleep 300", detach=True)
        #self.tmp_containers.append(container.id)
        await container.pause()
        await container.reload()
        assert container.status == "paused"
        await container.unpause()
        await container.reload()
        assert container.status == "running"

    async def test_logs(self, docker: AsyncDocker):
        container = await docker.containers.run("alpine", "echo hello world",
                                          detach=True)
        #self.tmp_containers.append(container.id)
        await container.wait()
        assert (await container.logs()) == b"hello world\n"

    async def test_exec_run_success(self, docker: AsyncDocker):
        container = await docker.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /test; sleep 60'", detach=True
        )
        #self.tmp_containers.append(container.id)
        exec_output = await container.exec_run("cat /test")
        assert exec_output.exit_code == 0
        assert exec_output.output == b"hello\n"

    async def test_exec_run_failed(self, docker: AsyncDocker):
        container = await docker.containers.run(
            "alpine", "sh -c 'sleep 60'", detach=True
        )
        #self.tmp_containers.append(container.id)
        exec_output = await container.exec_run("docker ps")
        assert exec_output.exit_code == 126
