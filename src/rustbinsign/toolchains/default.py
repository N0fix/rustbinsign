import os
import pathlib
from typing import Callable, Dict, List, Optional

from rustbininfo import Crate

from ..compilation import CompilationUnit
from ..logger import logger as log
from ..model import CompilationCtx
from ..rustup import get_rustup_home, rustup_install_toolchain
from .model import ToolchainModel


class DefaultToolchain(ToolchainModel):
    """
    Usage example:
    >>> tc = Toolchain(version)
    >>> pattern_file_list = tc.install()
    >>> std_libs: List[pathlib.Path] = tc.get_libs()
    """

    libs: Optional[List[pathlib.Path]]
    version: str
    toolchain_name: Optional[str]
    compile_unit: CompilationUnit
    _default_template: Dict
    _profile: Optional[str] = "release"

    def __init__(self, version: str, toolchain_name: Optional[str] = None):
        self.version = version
        self.libs = None
        self.toolchain_name = toolchain_name
        self.compile_unit = CompilationUnit(self)
        self.crate_transforms = {}
        self._default_template = {}

    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        return True

    def install(self) -> "self":
        log.debug(f"Downloading and installing toolchain version {self.name}")
        rustup_install_toolchain(self.version, self.toolchain_name)
        return self

    def compile_crate(
        self,
        crate: Crate,
        ctx: Optional[CompilationCtx] = None,
        toml_path: Optional[pathlib.Path] = None,
        compile_all: Optional[bool] = False,
    ):
        if ctx is None:
            ctx = CompilationCtx(template=self._default_template, profile=self._profile)

        unit = CompilationUnit(self, ctx)
        if toml_path:
            return unit.compile_crate(crate, toml_path, compile_all)

        return unit.compile_remote_crate(
            crate,
            crate_transform=self.crate_transforms.get(crate.name),
            compile_all=compile_all,
        )

    def get_libs(self):
        if self.libs is None:
            self.libs = self._gen_libs()

        self.libs = self._filter_libs(self.libs, lambda x: not "driver" in x.name)
        return self.libs

    def set_compilation_template(self, template: Optional[Dict]):
        if template is not None:
            self._default_template = template

        return self

    def set_compilation_profile(self, profile: str):
        self._profile = profile
        return self

    def _gen_libs(self):
        rustup_home = get_rustup_home()

        tc_path = pathlib.Path(rustup_home).joinpath("toolchains")
        target = None
        for _, dirs, _ in os.walk(tc_path):
            for directory in dirs:
                correct_version = directory.startswith(self.version)
                correct_toolchain = (
                    not self.toolchain_name or self.toolchain_name in directory
                )
                if correct_version and correct_toolchain:
                    target = directory
                    break

            break

        assert target is not None

        if self.toolchain_name is None:
            self.toolchain_name = target.split("-", 1)[1]

        # if "nt" in os.name: #XXX: removed due to potential cross compilation?
        libs = []
        libs_path = tc_path / pathlib.Path(target) / pathlib.Path("bin")
        libs += list(libs_path.glob("*.dll"))

        libs_path = (
            tc_path
            / pathlib.Path(target)
            / pathlib.Path("lib")
            / pathlib.Path("rustlib")
            / pathlib.Path(self.toolchain_name)
            / pathlib.Path("lib")
        )
        libs += list(libs_path.glob("*.dll"))

        # else:
        libs_path: pathlib.Path = (
            tc_path
            / pathlib.Path(target)
            / "lib"
            / "rustlib"
            / self.toolchain_name
            / "lib"
        )
        libs += list(libs_path.glob("*.so"))

        libs_path_self_contained = libs_path.joinpath(pathlib.Path("self-contained"))
        libs += list(libs_path_self_contained.glob("*.o"))
        if len(libs) == 0:
            raise ValueError("Please install the toolchain first using install()")

        return libs

    def _filter_libs(self, library_paths: List[pathlib.Path], custom_filter: Callable):
        res = []
        for lib in library_paths:
            if custom_filter(lib):
                res.append(lib)
        return res

    def _get_default_compilation_ctx(self):
        if self._default_template is not None:
            return CompilationCtx(template=self._default_template)

        return CompilationCtx
