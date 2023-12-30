import asyncio
from dockerxxx.client import AsyncDockerClient

async def amain():
    docker = AsyncDockerClient.from_env()

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

def main():
    asyncio.run(amain())

if __name__ == "__main__":
    main()
