import pathlib

from pydantic import Field

from ...model import Config


class ConfigPython(Config):
    target: pathlib.Path = Field(default=None)
