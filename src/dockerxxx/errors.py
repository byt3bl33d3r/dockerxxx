"""
https://github.com/docker/docker-py/blob/6ceb08273c157cbab7b5c77bd71e7389f1a6acc5/docker/errors.py
"""

class DockerException(Exception):
    """
    A base class from which all other exceptions inherit.

    If you want to catch all errors that the Docker SDK might raise,
    catch this base exception.
    """

class ContainerError(DockerException):
    """
    Represents a container that has exited with a non-zero exit code.
    """
    def __init__(self, container, exit_status, command, image, stderr):
        self.container = container
        self.exit_status = exit_status
        self.command = command
        self.image = image
        self.stderr = stderr

        err = f": {stderr}" if stderr is not None else ""
        super().__init__(
            f"Command '{command}' in image '{image}' "
            f"returned non-zero exit status {exit_status}{err}"
        )
