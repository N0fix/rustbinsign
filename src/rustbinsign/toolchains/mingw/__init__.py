import os
import pathlib
from typing import Callable, Dict, List, Optional

import requests
from rustbininfo import Crate

from ...compilation import CompilationUnit
from ...logger import logger as log
from ...model import CompilationCtx
from ...rustup import get_rustup_home, rustup_install_toolchain
from ...util import extract_tarfile, get_default_dest_dir
from ..default import DefaultToolchain


class MinGWToolchain(DefaultToolchain):
    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        return "x86_64-pc-windows-gnu" == toolchain_name

    def get_libs(self):
        if self.libs is None:
            # self.libs = self._gen_libs()
            self.libs = []
            self.libs = self._filter_libs(self.libs, lambda x: not "driver" in x.name)
            self.libs += self._gen_hello_world(self._default_template)

        return self.libs

    def _gen_hello_world(self, template: Optional[pathlib.Path]):
        log.info("Generating hello world package")
        c = Crate.from_depstring("hello-world-2022-10-01-0.1.0")

        template = {key: template[key] for key in template if key != "lib"}

        args = {
            "profile": "release",
            "lib": False,
            "template": template,
        }

        if template is not None:
            args["template"] = template

        return CompilationUnit(self, CompilationCtx(**args)).compile_remote_crate(c)
