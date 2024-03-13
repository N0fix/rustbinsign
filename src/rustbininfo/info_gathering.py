import hashlib
import pathlib
import re
from typing import List, Optional, Set, Tuple

import requests
from pydantic import BaseModel

from .logger import logger as log
from .model import Crate


def _extract_rustc_commit(target: pathlib.Path):
    data = open(target, "rb").read()
    res = re.search(b"rustc/([a-z0-9]{40})", data)
    return res.group(0)[len("rustc/") :].decode()


def _get_version_from_commit(commit: str):
    url = f"https://github.com/rust-lang/rust/branch_commits/{commit}"
    res = requests.get(url, timeout=20).text
    regex = re.compile(r'href="/rust-lang/rust/releases/tag/([0-9\.]+)"')
    if not regex.findall(res):
        return None
    return regex.findall(res)[-1]


def _get_latest_rustc_version():
    url = "https://github.com/rust-lang/rust/tags"
    res = requests.get(url, timeout=20).text
    regex = re.compile(r"/rust-lang/rust/releases/tag/([0-9\.]+)")
    return regex.findall(res)[0]


def get_rustc_version(target: pathlib.Path) -> Tuple[str, str]:
    commit = _extract_rustc_commit(target)
    log.debug(f"Found commit {commit}")
    version = _get_version_from_commit(commit)
    if version is None:
        log.debug(f"No tag matching this commit, getting latest version")
        return _get_latest_rustc_version()

    log.debug(f"Found tag {version}")
    return commit, version


def get_dependencies(target: pathlib.Path) -> Set[Crate]:
    result = []
    data = open(target, "rb").read()
    res = re.findall(rb"registry.src.[^\\\/]+.([^\\\/]+)", data)
    for dep in set(res):
        try:
            dep = dep[: dep.index(b"\x00")]
        except:
            pass

        if dep == b'':
            continue
        log.debug(f"Found dependency : {dep}")
        c = Crate.from_depstring(dep.decode(), fast_load=False)
        if c.name != "rustc-demangle":
            result.append(c)
    return set(result)


def guess_is_debug(target: pathlib.Path) -> bool:
    # needle = b"run with `RUST_BACKTRACE=1` environment variable to display a backtrace"
    # data = open(target, "rb").read()
    # return needle in data
    return False


def guess_toolchain(target_content: bytes) -> Optional[str]:
    known_heuristics = {
        b"Mingw-w64 runtime failure": "Mingw-w64",
        b"_CxxThrowException": "windows-msvc",
        b".CRT$": "windows-msvc",
        b"/checkout/src/llvm-project/libunwind/src/DwarfInstructions.hpp": "linux-musl",
    }

    for item, value in known_heuristics.items():
        if item in target_content:
            return value

    return None


def imphash(dependencies: List[Crate]):
    md5 = hashlib.md5()
    sorted_list = sorted([str(d) for d in dependencies])
    for dep in sorted_list:
        md5.update(str(dep).encode())

    return md5.hexdigest()

class TargetRustInfo(BaseModel):
    rustc_version: str
    rustc_commit_hash: str
    dependencies: List[Crate]
    rust_dependencies_import_hash: str
    guessed_toolchain: Optional[str] = None
    guess_is_debug_build: bool

    @classmethod
    def from_target(cls, path: pathlib.Path):
        content = open(path, "rb").read()
        commit, version = get_rustc_version(path)
        dependencies: Set[Crate] = get_dependencies(path)
        dependencies = sorted(list(dependencies), key=lambda x: x.name)

        return TargetRustInfo(
            rustc_commit_hash=commit,
            rustc_version=version,
            dependencies=dependencies,
            rust_dependencies_import_hash=imphash(dependencies),
            guessed_toolchain=guess_toolchain(content),
            guess_is_debug_build=guess_is_debug(path),
        )
