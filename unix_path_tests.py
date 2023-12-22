import asyncio
import asyncssh
import secrets
import httpx
from pprint import pprint
from pydantic import AnyUrl

async def amain():
    ssh_url = AnyUrl("ssh://127.0.0.1:2222")
    local_uds = AnyUrl(f"unix://tmp/{secrets.token_hex(nbytes=6)}.sock")
    local_uds = f"/{local_uds.host}{local_uds.path}"

    dest_uds = "/var/run/docker.sock"
    options = asyncssh.SSHClientConnectionOptions(
        username="vscode",
        password="vscode",
        client_keys=[]
    )

    conn = await asyncssh.connect(host=ssh_url.host, port=ssh_url.port, options=options)
    pprint(await conn.run("id"))
    print(f"{local_uds} -> {dest_uds}")

    listener = await conn.forward_local_path(listen_path=local_uds, dest_path=dest_uds)

    transport = httpx.AsyncHTTPTransport(uds=local_uds, retries=3)
    client = httpx.AsyncClient(transport=transport, base_url="http://docker")

    r = await client.get("/info")
    pprint(r.json())

asyncio.run(amain())