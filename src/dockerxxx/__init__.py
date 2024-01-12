import importlib.metadata

__version__ = importlib.metadata.version("dockerxxx")

from .client import Docker
from .client import AsyncDocker

__all__ = [
    "Docker",
    "AsyncDocker"
]