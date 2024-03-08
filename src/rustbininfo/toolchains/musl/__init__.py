import os
import pathlib
from typing import Callable, Dict, List, Optional

import requests

from ...compilation import CompilationUnit
from ...logger import logger as log
from ...model import CompilationCtx, Crate
from ...rustup import get_rustup_home, rustup_install_toolchain
from ...util import extract_tarfile, get_default_dest_dir
from ..default import DefaultToolchain
from .transforms import hyper

TRANSFORMS = {"hyper": hyper.transform}


class MuslToolchain(DefaultToolchain):
    musl_lib_path: pathlib.Path

    def __init__(
        self,
        version: str,
        toolchain_name: Optional[str] = None,
        # compilation_template: Optional[dict] = None,
    ):
        assert os.name != "nt"

        super().__init__(version, toolchain_name)
        self._default_template = {"release": {"debug": 2, "strip": "none"}}
        self.musl_lib_path = None
        self.crate_transforms = TRANSFORMS
        self.musl_target_name = "x86_64-linux-musl-native.tgz"

    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        return "x86_64-unknown-linux-musl" == toolchain_name

    def install(self) -> "self":
        log.warning("MUSL toolchain requieres musl, musl-dev and musl-tools packages to be installed.")
        log.debug(f"Downloading and installing toolchain version {self.name}")
        rustup_install_toolchain(self.version, self.toolchain_name)

        musl_dir = get_default_dest_dir().joinpath("x86_64-linux-musl-native")
        if musl_dir.exists():
            self.musl_lib_path = musl_dir / "lib"

        else:
            self.musl_lib_path = self._setup_musl()

        return self

    def compile_crate(self, crate: Crate, ctx: CompilationCtx = None):
        assert self.musl_lib_path is not None  # call install() first !

        if ctx is None:
            ctx = self._get_default_compilation_ctx()

        ctx.env |= {
            "LD_LIBRARY_PATH": str(self.musl_lib_path),
            "RUSTFLAGS": "-C target-feature=-crt-static",
        }

        return super().compile_crate(crate, ctx)

    def get_libs(self):
        if self.libs is None:
            # self.libs = self._gen_libs()
            self.libs=[]
            self.libs = self._filter_libs(self.libs, lambda x: not "driver" in x.name)
            self.libs += self._gen_hello_world(self._default_template)

        return self.libs

    def _download_musl(self):
        log.debug("Download musl")

        name = self.musl_target_name
        url = f"https://musl.cc/{name}"

        headers = {"User-Agent": "rustbininfo (https://github.com/N0fix/rustbininfo)"}
        res = requests.get(url, timeout=20, headers=headers)
        assert res.status_code == 200

        result_file = get_default_dest_dir().joinpath(name)
        open(result_file, "wb+").write(res.content)

        log.debug(f"Successfuly downloaded to {result_file}")
        return result_file

    def _setup_musl(self):
        log.debug("Setup musl")
        musl_path = self._download_musl()
        directory = extract_tarfile(musl_path)
        musl_lib_path = pathlib.Path(directory) / "lib"
        return musl_lib_path

    def _gen_hello_world(self, template: Optional[pathlib.Path]):
        log.info("Generating hello world package")
        c = Crate.from_depstring("hello-world-2022-10-01-0.1.0")

        template = {key: template[key] for key in template if key != "lib"}

        args = {
            "profile": "release",
            "lib": False,
            "env": {
                "LD_LIBRARY_PATH": str(self.musl_lib_path),
                # "RUSTFLAGS": "-C target-feature=-crt-static",
            },
            "template": template,
        }

        if template is not None:
            args["template"] = template

        return CompilationUnit(self, CompilationCtx(**args)).compile_remote_crate(c)


class MuslToolchain_x86(MuslToolchain):
    musl_lib_path: pathlib.Path

    def __init__(
        self,
        version: str,
        toolchain_name: Optional[str] = None,
    ):
        assert os.name != "nt"

        super().__init__(version, toolchain_name)
        self.musl_target_name = "i686-linux-musl-native.tgz"

    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        return "i686-unknown-linux-musl" == toolchain_name
