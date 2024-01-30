import os
import pathlib
from typing import Callable, Dict, List, Optional

from ..compilation import CompilationUnit
from ..logger import logger as log
from ..model import CompilationCtx, Crate
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
    _version: str
    _toolchain_name: Optional[str]
    compile_unit: CompilationUnit
    _default_template: Dict

    def __init__(self, version: str, toolchain_name: Optional[str] = None):
        self._version = version
        self.libs = None
        self._toolchain_name = toolchain_name
        self.compile_unit = CompilationUnit(self)
        self.crate_transforms = {}
        self._default_template = None

    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        return True

    def install(self) -> "self":
        log.debug(f"Downloading and installing toolchain version {self.name}")
        rustup_install_toolchain(self.name)
        return self

    def compile_crate(self, crate: Crate, ctx: CompilationCtx = CompilationCtx()):
        unit = CompilationUnit(self, ctx)
        return unit.compile_remote_crate(crate, self.crate_transforms.get(crate.name))

    def get_libs(self):
        if self.libs is None:
            self.libs = self._gen_libs()

        self.libs = self._filter_libs(self.libs, lambda x: not "driver" in x.name)
        return self.libs

    def set_default_compilation_template(self, template: Dict):
        self._default_template = template

    def _gen_libs(self):
        rustup_home = get_rustup_home()

        tc_path = pathlib.Path(rustup_home).joinpath("toolchains")
        target = None
        for _, dirs, _ in os.walk(tc_path):
            for directory in dirs:
                correct_version = directory.startswith(self._version)
                correct_toolchain = (
                    not self._toolchain_name or self._toolchain_name in directory
                )
                if correct_version and correct_toolchain:
                    target = directory
                    break

            break

        assert target is not None

        if self._toolchain_name is None:
            self._toolchain_name = target.split("-", 1)[1]

        # if "nt" in os.name: #XXX: removed due to potential cross compilation?
        libs_path = tc_path / pathlib.Path(target) / pathlib.Path("bin")
        libs = []
        libs += list(libs_path.glob("*.dll"))

        # else:
        libs_path: pathlib.Path = (
            tc_path
            / pathlib.Path(target)
            / "lib"
            / "rustlib"
            / self._toolchain_name
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
