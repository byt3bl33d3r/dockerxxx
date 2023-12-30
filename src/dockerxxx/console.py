import typer
import asyncio
import structlog
from pprint import pprint
from .client import AsyncDockerClient

async def amain():
    docker = AsyncDockerClient.from_env()
    #pprint(await docker.daemon_version())
    #pprint(await docker.info())
    await docker.ping()
    try:
        container = await docker.containers.create('alpine', 'cat', open_stdin=True)

        stream, sock = await container.attach_socket(stdin=True)
        await container.start()

        await sock.write(b'sent data')
        await sock.aclose()
        await stream.aclose()

        status = await container.wait()
        stdout = await container.logs(stderr=False)
        stderr = await container.logs(stdout=False)

        print(f"status code: {status.status_code}")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
    finally:
        await container.remove()

    #pprint(await docker.images.list())
    #pprint(await docker.containers.get("0201f1f3626e"))
    #c = await docker.containers.list()
    #pprint(c)
    #pprint(await docker.images.list())
    #pprint(await c[0].top())
    #pprint(await c[0].exec_run('id'))
    #pprint(await c[0].logs())
    #pprint(await docker.containers.run('alpine', '', remove=True))

def main():
    structlog.reset_defaults()
    asyncio.run(amain())

if __name__ == "__main__":
    typer.run(main)
