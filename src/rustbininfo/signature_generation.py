import os
import pathlib
from typing import Callable, List, Optional

from .logger import logger as log
from .rustup import get_rustup_home, install_toolchain


class Toolchain:
    """
    Usage example:
    >>> tc = Toolchain(version)
    >>> pattern_file_list = tc.install()
    >>> std_libs: List[pathlib.Path] = tc.libs
    """

    version: str
    libs: Optional[List[pathlib.Path]]

    def __init__(self, version: str):
        self.version = version
        self._libs = None

    def install(self) -> "Toolchain":
        log.debug(f"Downloading and installing toolchain version {self.version}")
        install_toolchain(self.version)
        return self

    @property
    def libs(self):
        if self._libs is None:
            rustup_home = get_rustup_home()

            tc_path = pathlib.Path(rustup_home).joinpath("toolchains")
            target = None
            for _, dirs, _ in os.walk(tc_path):
                for directory in dirs:
                    if directory.startswith(self.version):
                        target = directory
                        break
                break

            if os.name == "nt":
                libs_path = tc_path / pathlib.Path(target) / pathlib.Path("bin")
                self._libs = list(libs_path.glob("*.dll"))

            else:
                libs_path = tc_path / pathlib.Path(target) / pathlib.Path("lib")
                self._libs = list(libs_path.glob("*.so"))

            if len(self._libs) == 0:
                raise ValueError("Please install the toolchain first using install()")

        self.libs = self._filter_libs(self._libs, lambda x: not "driver" in x.name)
        return self._libs

    @libs.setter
    def libs(self, libs):
        self._libs = libs

    def _filter_libs(self, library_paths: List[pathlib.Path], custom_filter: Callable):
        res = []
        for lib in library_paths:
            if custom_filter(lib):
                res.append(lib)
        return res
