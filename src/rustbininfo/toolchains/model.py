import pathlib
from abc import ABC
from typing import Dict, List, Optional

from ..compilation import CompilationUnit
from ..model import CompilationCtx, Crate


class ToolchainModel(ABC):
    libs: Optional[List[pathlib.Path]] = None
    compile_unit: CompilationUnit
    _default_template: Optional[Dict] = None
    _toolchain_name: Optional[str] = None
    _version: str

    @classmethod
    def match_toolchain(cls, toolchain_name: str):
        ...

    def install(self) -> "self":
        ...

    def compile_crate(self, crate: Crate, ctx: CompilationCtx = None):
        ...

    def get_libs(self):
        ...

    def set_default_compilation_template(self, template: Dict):
        ...

    @property
    def name(self):
        name = self._version
        if self._toolchain_name is not None and self._toolchain_name:
            name = f"{name}-{self._toolchain_name}"

        return name
