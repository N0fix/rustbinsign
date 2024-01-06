import copy
import json
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Text

import toml

from .model import Crate


def remove_line(filepath: Path, line_nb: int):
    lines = open(filepath, "r").readlines()
    with open(filepath, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines):
            if i != line_nb:
                f.write(line)


def add_panic_code_to_project(project_path: Path):
    NO_PANIC_CODE = """
use core::panic::PanicInfo;

/// This function is called on panic.
#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}
"""
    for dirpath, dirnames, filenames in os.walk(project_path):
        for filename in [f for f in filenames if f.endswith(".rs")]:
            if filename == "lib.rs":
                open(os.path.join(dirpath, filename), "a", encoding="utf-8").write(
                    NO_PANIC_CODE
                )


def remove_no_std_from_project(project_path: Path):
    for dirpath, dirnames, filenames in os.walk(project_path):
        for filename in [f for f in filenames if f.endswith(".rs")]:
            filepath = os.path.join(dirpath, filename)
            content = open(filepath, "r", encoding="utf-8").read()
            for i, line in enumerate(content.splitlines()):
                if line.strip() == "#![no_std]":
                    remove_line(filepath, i)


def setup_toml(toml_path: Path):
    # We want to be able to compile projects as shared libraries, which can have debug symbols and are easy to parse
    remove_no_std_from_project(toml_path.parent)
    crate_toml = toml.load(toml_path)
    crate_toml["lib"] = {"crate-type": ["dylib"]}
    crate_toml["profile"] = {
        "release": {"debug": 2, "panic": "abort"},  # Usefull for no-std crates
        "dev": {"debug": 2, "panic": "abort"},  # Usefull for no-std crates
    }
    safe_iter = copy.deepcopy(crate_toml)

    # Handle corner cases where some fields of Toml would have \" , which seems to be broken when using python's toml lib
    # See sha2's Cargo.toml for an example
    for x, y in safe_iter.items():
        if isinstance(y, dict):
            for k, v in y.items():
                if "\\" in k:
                    val = crate_toml[x][k]
                    del crate_toml[x][k]
                    crate_toml[x][k.replace("\\", "")] = val

    toml.dump(crate_toml, open(toml_path, "w+", encoding="utf-8"))


def _compile_with_cargo(
    toml_path: Path,
    rustc_version: str,
    release: bool = True,
    features: Optional[List[Text]] = [],
) -> bool:
    args = [
        "rustup",
        "run",
        rustc_version,
        "cargo",
        "build",
        "--lib",
    ]

    if release:
        args.append("--release")

    if features:
        args.append("--features")
        args.append(
            ",".join(list(filter(lambda f: f not in ["nightly", "default"], features)))
        )

    print(" ".join(args))
    ret = subprocess.run(
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=toml_path.parent
    )

    if ret.returncode == 0:
        return True

    if features:  # Remaining features to test compilation with
        # Removing one feature and try to compile again
        print(f"Compilation failed, retrying with features : {features[1:]}")
        return _compile_with_cargo(toml_path, rustc_version, release, features[1:])

    return False


def compile_crate(
    crate: Crate, toml_path: Path, rustc_version: str, release: bool = True
):
    mode = "release" if release else "debug"
    setup_toml(toml_path)
    print(f"Compiling {crate.name}")
    if _compile_with_cargo(toml_path, rustc_version, release, crate.features):
        if os.name == "nt":
            print(toml_path.parent.joinpath(*["target", mode]))
            return list(toml_path.parent.joinpath(*["target", mode]).glob("*.dll"))

        else:
            return list(toml_path.parent.joinpath(*["target", mode]).glob("*.so"))
