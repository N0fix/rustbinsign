import pathlib
import re
from typing import Set, Tuple
from pydantic import BaseModel

import requests

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
    res = re.findall(rb"cargo.registry.src.[^\\\/]+.([^\\\/]+)", data)
    for dep in set(res):
        try:
            dep = dep[:dep.index(b'\x00')]
        except:
            pass
        log.debug(f"Found dependency : {dep}")
        c = Crate.from_depstring(dep.decode())
        if c.name != "rustc-demangle":
            result.append(c)
    return set(result)


def guess_is_debug(target: pathlib.Path) -> bool:
    needle = b"there is no such thing as"
    data = open(target, "rb").read()
    return needle in data


class TargetRustInfo(BaseModel):
    rustc_version: str
    rustc_commit_hash: str
    dependencies: Set[Crate]
    # experimental_guess_is_debug_build: bool

    @classmethod
    def from_target(cls, path: pathlib.Path):
        commit, version = get_rustc_version(path)
        dependencies: Set[Crate] = get_dependencies(path)
        return TargetRustInfo(
            rustc_commit_hash=commit,
            rustc_version=version,
            dependencies=dependencies,
            # experimental_guess_is_debug_build=guess_is_debug(path),
        )
