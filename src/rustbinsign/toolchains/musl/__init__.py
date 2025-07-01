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
        log.warning(
            "MUSL toolchain requieres musl, musl-dev and musl-tools packages to be installed."
        )
        log.debug(f"Downloading and installing toolchain version {self.name}")
        rustup_install_toolchain(self.version, self.toolchain_name)

        musl_dir = get_default_dest_dir().joinpath("x86_64-linux-musl-native")
        if musl_dir.exists():
            self.musl_lib_path = musl_dir / "lib"

        else:
            self.musl_lib_path = self._setup_musl()

        return self

    def _compile_setup_ctx(self, ctx) -> CompilationCtx:
        assert self.musl_lib_path is not None  # call install() first !

        if ctx is None:
            ctx = self._get_default_compilation_ctx()

        ctx.env |= {
            "LD_LIBRARY_PATH": str(self.musl_lib_path),
        }
        if ctx.lib:
            # warning: -crt-static only works when building lib
            ctx.env |= {
                "RUSTFLAGS": ctx.env.get("RUSTFLAGS", "") + " -C target-feature=-crt-static",
            }

        return ctx

    def compile_remote_crate(self, crate: Crate, ctx: Optional[CompilationCtx] = None, compile_all: bool = False):
        if compile_all:
            ctx.lib = False
        ctx = self._compile_setup_ctx(ctx)
        return super().compile_remote_crate(crate, ctx, compile_all)

    def compile_project(
        self,
        toml_path: pathlib.Path,
        ctx: CompilationCtx | None = None,
        features: Optional[list[str]] = (),
        verb: str | None = "build",
        additional_args: list[str] = [],
    ):
        ctx = self._compile_setup_ctx(ctx)
        return super().compile_project(toml_path, features=features, verb=verb, additional_args=additional_args)

    def get_libs(self):
        if self.libs is None:
            # self.libs = self._gen_libs()
            self.libs = []
            self.libs = self._filter_libs(self.libs, lambda x: "driver" not in x.name)
            self.libs += self._gen_hello_world(self._default_template)

        return self.libs

    def _download_musl(self):
        log.debug("Download musl")

        name = self.musl_target_name
        url = f"https://musl.cc/{name}"

        headers = {"User-Agent": "rustbinsign (https://github.com/N0fix/rustbinsign)"}
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
                # "RUSTFLAGS": ctx.env.get("RUSTFLAGS", "") + " -C target-feature=-crt-static",
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
