import asyncio
from dockerxxx import AsyncDocker

async def amain():
    docker = await AsyncDocker.from_env()
    await docker.containers.run("ubuntu", "echo hello world")
    await docker.containers.run("bfirsh/reticulate-splines", detach=True)

    print(await docker.containers.list())

    container = await docker.containers.get('45e6d2de7c54')
    print(container.config.image)
    print(await container.logs())
    await container.stop()

    async for line in await container.logs(stream=True):
        print(line.strip())

    await docker.images.pull('nginx')
    print(await docker.images.list())

def main():
    asyncio.run(amain())

if __name__ == "__main__":
    main()
