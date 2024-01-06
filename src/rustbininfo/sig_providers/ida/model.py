import pathlib
from ...model import Config


class ConfigIDA(Config):
    idat: pathlib.Path
    # pattern_generator: pathlib.Path
    sigmake: pathlib.Path
