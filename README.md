# DockerXXX 🥴

An orgasmic Python library for the Docker Engine API. It lets you do anything the `docker` command does, but from within Python apps – run containers, manage containers, manage Swarms, etc.

## Installation

The latest stable version [is available on PyPI](https://pypi.python.org/pypi/docker/). Either add `docker` to your `requirements.txt` file or install with pip:

    pip install dockerxxx


## Usage

## Developer Notes

```
datamodel-codegen --input docker-v1.43.yaml --input-file-type openapi --output src/dockerxxx/models.py --target-python-version 3.10 --use-schema-description --snake-case-field --collapse-root-models
```

To convert from swagger 2.0 to OpenAPI 3.0 https://stackoverflow.com/a/59749691
