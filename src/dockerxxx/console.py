import typer
import asyncio
from pprint import pprint
from .client import AsyncDockerClient


async def amain():
    docker = AsyncDockerClient.from_env()
    pprint(await docker.daemon_version())
    pprint(await docker.info())
    #pprint(await docker.images.list())
    #pprint(await docker.containers.get("0201f1f3626e"))
    #c = await docker.containers.list()
    #pprint(c)
    #pprint(await docker.images.list())
    #pprint(await c[0].top())
    #pprint(await c[0].exec_run('id'))
    #pprint(await c[0].logs())
    pprint(await docker.containers.run('alpine', 'echo hello world', remove=True))


def main():
    asyncio.run(amain())

if __name__ == "__main__":
    typer.run(main)
