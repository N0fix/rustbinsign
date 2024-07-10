import pathlib
from abc import ABC
from typing import Dict, List, Optional

from rustbininfo import Crate

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

    def compile_crate(
        self,
        crate: Crate,
        ctx: CompilationCtx = CompilationCtx(),
        toml_path: Optional[pathlib.Path] = None,
        compile_all: Optional[bool] = False,
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
