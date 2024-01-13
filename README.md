# DockerXXX 🥴

An **💦 orgasmic 💦** Python library for the Docker Engine API. It lets you do *almost* anything the `docker` command does, but from within Python apps – run containers, manage containers, ~~manage Swarms~~, etc.

This is meant to be a modern, async-first, *mostly* drop-in replacement for the official [Docker SDK for Python](https://github.com/docker/docker-py) library:

- Needs Python 3.10 or above
- Async first 🚀
- First class support for Docker over SSH & HTTP:
    - Uses [HTTPX](https://www.python-httpx.org/) as the HTTP client
    - Uses [asyncssh](https://asyncssh.readthedocs.io/en/latest/) for Docker over SSH
- Uses [Pydantic](https://docs.pydantic.dev/latest/) for request/response validation
- Structured logging using [structlog](https://www.structlog.org/en/stable/) 🪵
- Comprehensive Tests 🧪

## Installation
> [!WARNING]
> This library is in beta, if something breaks don't blame me (but feel free to open an issue 🪳 or even better open a PR 🥵)

<!---
The latest stable version [is available on PyPI](https://pypi.python.org/pypi/docker/). Either add `docker` to your `requirements.txt` file or install with pip:

    pip install dockerxxx

--> 

For now install directly from Git:

    pip3 install git+https://github.com/byt3bl33d3r/dockerxxx.git

## What works and how well?

I'm striving for 1 to 1 feature parity with the official library (with the exception of Swarm-related functionality). As of writing this is beta software, take a look at the tests and the examples folder for to get a clear idea of what works.

> [!NOTE]
> The existence of tests doesn't imply that they're all currently passing

| API | Implemented | Tests  |
| --- | --- | -- |
| Containers | 80% | ✅ |
| Exec | 90% | ✅ |
| Images | 80% | ✅ | 
| Networks | 100% | ✅ |
| Nodes | 0% (Not Planned) | N/A |
| Plugins | 0% | ❌ |
| Secrets | 0% | ❌ |
| Services | 0% (Not Planned) | N/A |
| Swarm | 0% (Not Planned) | N/A |
| Volumes | 100% | ✅ |

## Usage

Connect to Docker using the default socket or the configuration in your environment:

```python
from dockerxxx import AsyncDocker
client = await AsyncDocker.from_env()
```

You can run containers:

```python
>>> await client.containers.run("ubuntu:latest", "echo hello world")
b'hello world\n'
```

You can run containers in the background:

```python
>>> await client.containers.run("bfirsh/reticulate-splines", detach=True)
<Container '45e6d2de7c54'>
```

You can manage containers:

```python
>>> await client.containers.list()
[<Container '45e6d2de7c54'>, <Container 'db18e4f20eaa'>, ...]

>>> container = await client.containers.get('45e6d2de7c54')

>>> container.config.image
"bfirsh/reticulate-splines"

>>> await container.logs()
"Reticulating spline 1...\n"

>>> await container.stop()
```

You can stream logs:

```python
>>> async for line in await container.logs(stream=True):
...   print(line.strip())
Reticulating spline 2...
Reticulating spline 3...
...
```

You can manage images:

```python
>>> await client.images.pull('nginx')
<Image 'nginx'>

>>> await client.images.list()
[<Image 'ubuntu'>, <Image 'nginx'>, ...]
```

## FAQ

### Why ?

The official [Docker SDK for Python](https://github.com/docker/docker-py) is lacking several features that I really needed and development on the library seems to be "maintanance". Also, since it's inception, a lot of libraries have been made that can simplify the codebase significantly. Thought I'd give it a shot at writing my own. Exisiting async Python Docker libraries are lacking in features and/or aren't a drop-in replacement for the official library. 

### ... What's with the name and can you change it ffs?

`dockerx` (my first choice) is already taken on PyPI, `dockerxx` seemed dumb and doesn't make any sense, `dockerxxx` is spicy 🌶️. I might change the name once feature parity is achieved with the official library cause I know people/corps hate "non-professional" names blah blah blah, It'll hinder adoption blah blah blah but for now let a guy inject some humor into his life will ya?
