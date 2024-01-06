import pathlib
from typing import List

from ..info_gathering import get_dependencies, get_rustc_version
from ..model import Crate


def info_subcommand(target: pathlib.Path):
    if not target.exists():
        print(f"{target} do not exists")
        exit(1)

    dependencies: List[Crate] = get_dependencies(target)
    commit, version = get_rustc_version(target)
    print("[----    rustc     ----]")
    print(f"version: ~{version} ({commit})\n")
    print(f"[---- Dependencies ----]")

    for dep in dependencies:
        print(f"{dep}")
