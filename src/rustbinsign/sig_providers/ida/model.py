import pathlib
import shutil
import sys

from pydantic import Field

from ...model import Config


class ConfigIDA(Config):
    idat: pathlib.Path = Field(default=None)
    # pattern_generator: pathlib.Path
    sigmake: pathlib.Path = Field(default=None)

    def model_post_init(self, __context):
        # ida64 should work for both 32 and 64 bits executables since IDA 8 or so
        if not shutil.which("idat64"):
            print('Could not find "idat64" in your Path, aborting.', file=sys.stderr)
            exit(1)

        if not shutil.which("sigmake"):
            print('Could not find "sigmake" in your Path, aborting.', file=sys.stderr)
            exit(1)

        self.idat = pathlib.Path(shutil.which("idat64"))
        self.sigmake = pathlib.Path(shutil.which("sigmake"))
