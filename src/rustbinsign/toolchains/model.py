import pathlib
from abc import ABC
from typing import Dict, List, Optional

from ..compilation import CompilationUnit
from ..model import CompilationCtx


class ToolchainModel(ABC):
    libs: Optional[List[pathlib.Path]] = None
    compile_unit: CompilationUnit
    _default_template: Optional[Dict] = None
    toolchain_name: Optional[str] = None
    version: str

    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        ...

    def install(self) -> "self":
        ...

    def compile_remote_crate(self, crate, ctx: Optional[CompilationCtx] = None, compile_all: bool = False): ...

    def compile_project(
        self,
        toml_path: pathlib.Path,
        ctx: CompilationCtx | None = None,
        features: list[str] = (),
        verb: str | None = "build",
        additional_args: list[str] = (),
    ):
        ...

    def get_libs(self):
        ...

    def set_default_compilation_template(self, template: Dict):
        ...

    @property
    def name(self):
        name = self.version
        if self.toolchain_name is not None and self.toolchain_name:
            name = f"{name}-{self.toolchain_name}"

        return name
