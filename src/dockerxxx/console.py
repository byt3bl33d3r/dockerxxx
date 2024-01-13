import typer
import asyncio
import structlog
from pprint import pprint
from .client import AsyncDocker

async def amain():
    docker = await AsyncDocker.from_env()
    #pprint(await docker.daemon_version())
    #pprint(await docker.info())
    pprint(await docker.ping())
    #pprint(await docker.containers.list())
    #pprint(await docker.images.pull('nginx'))
    #network = await docker.networks.create('wassup', labels={'foo': 'bar'})
    #pprint(await docker.images.list())
    #pprint(network)
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
