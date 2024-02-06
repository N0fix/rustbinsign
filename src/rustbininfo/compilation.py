import copy
import os
import pathlib
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Text

import parse
import toml
from git import Repo, TagReference

from .exceptions import CompilationError
from .logger import logger as log
from .model import CompilationCtx, Crate
from .util import extract_tarfile, get_default_dest_dir


# Unused yet
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


def remove_line(filepath: Path, line_nb: int):
    lines = open(filepath, "r", encoding="utf-8").readlines()
    with open(filepath, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines):
            if i != line_nb:
                f.write(line)


def remove_no_std_from_project(project_path: Path):
    for dirpath, dirnames, filenames in os.walk(project_path):
        for filename in [f for f in filenames if f.endswith(".rs")]:
            filepath = os.path.join(dirpath, filename)
            content = open(filepath, "r", encoding="utf-8").read()
            for i, line in enumerate(content.splitlines()):
                if line.strip() == "#![no_std]":
                    remove_line(filepath, i)


def setup_toml(toml_path: Path, template: Dict):
    custom_options = template

    # We want to be able to compile projects as shared libraries, which can have debug symbols and are easy to parse
    remove_no_std_from_project(toml_path.parent)
    crate_toml = toml.load(toml_path)
    crate_toml |= custom_options
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

    toml.dump(crate_toml, open(toml_path, "w", encoding="utf-8"))


class CompilationUnit:
    tc: "Toolchain"
    ctx: CompilationCtx

    def __init__(self, toolchain, ctx: CompilationCtx = None):
        if ctx is None:
            ctx = CompilationCtx()

        self.ctx = ctx
        self.tc = toolchain

    def _setup_repo(self, crate: Crate):
        repo_path = get_default_dest_dir().joinpath(crate.name)

        try:
            repo = Repo.clone_from(crate.repository, repo_path)

        except:
            log.error(
                f"Could not clone {crate.repository} to {repo_path}, assuming that the repo is cloned already"
            )
            repo = Repo(repo_path)

        # Nothing standard, but most repos should have something like this
        seeked_tags = [
            f"{crate.name}-{crate.version}",
            f"{crate.name}-v{crate.version}",
            f"{crate.name}_{crate.version}",
            f"{crate.name}_v{crate.version}",
            f"{crate.version}",
            f"v{crate.version}",
        ]

        found_tag = None

        for tag in TagReference.list_items(repo):
            if tag.name in seeked_tags:
                found_tag = tag

        if found_tag is not None:
            log.debug(f"Found tag {found_tag}, checking out")
            repo.git.checkout(found_tag)

        return repo_path

    def _cargo_build(
        self,
        project_path: pathlib.Path,
        crate: Crate,
        features: Optional[List[Text]] = (),
        post_verb: Optional[List[Text]] = (),
        additional_env: Optional[Dict] = None,
    ):
        args = [
            "rustup",
            "run",
            self.tc.name,
            "cargo",
            "build",
            # "--no-run",
            # "--profile",
            # "release",
        ]

        args += list(post_verb)

        if features:
            args.append("--features")
            args.append(
                ",".join(
                    list(filter(lambda f: f not in ["nightly", "default"], features))
                )
            )

        env = os.environ.copy()
        if env is not None:
            # Custom environ setup
            if additional_env:
                for key, val in self.ctx.env.items():
                    env[key] = val

        log.debug(f'{" ".join(args)} || With env : {self.ctx.env}')

        ret = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_path,
            env=env,
        )

        if ret.returncode == 0:
            return ret.returncode, ret.stdout, ret.stderr

        if features:  # Remaining features to test compilation with
            # Removing one feature and try to compile again
            log.debug(f"Compilation failed, retrying with features : {features[1:]}")
            return self._cargo_build(
                project_path, crate, features[1:], post_verb, additional_env
            )

        return ret.returncode, ret.stdout, ret.stderr

    def compile_examples(self, crate: Crate, features: Optional[List[Text]] = ()):
        repo_path = self._setup_repo(crate)
        log.info("Compiling tests, it might take minutes")

        # I guess output path could be customisable, so this is not guaranteed to work.
        code, out, err = self._cargo_build(repo_path, crate, features, ["--tests", "--profile", "release" if self.ctx.profile == "release" else "dev"])
        code, out, err = self._cargo_build(repo_path, crate, features, ["--benches", "--profile", "release" if self.ctx.profile == "release" else "dev"])
        code, out, err = self._cargo_build(repo_path, crate, features, ["--examples", "--profile", "release" if self.ctx.profile == "release" else "dev"])



        # targets = []

        # for line in ret.stderr.decode("utf-8").splitlines():
        #     if "Executable" in line:
        #         t = parse.parse(
        #             "{}Executable {}.rs ({target})", line, case_sensitive=True
        #         )
        #         targets.append(t["target"])
        # list(filter(lambda i: i is not None, targets))
        

    def compile_crate(
        self, crate: Crate, toml_path: Path, crate_transform: Optional[Callable] = None
    ) -> List[pathlib.Path]:
        setup_toml(toml_path, self.ctx.template)

        log.info(f"Compiling {crate.name}")
        if self._compile_with_cargo(toml_path, crate.features):
            if os.name == "nt":
                extension = "*.dll"

                if not self.ctx.lib:
                    extension = "*.exe"

                return list(
                    toml_path.parent.joinpath(*["target", self.ctx.profile]).glob(
                        extension
                    )
                )

            else:
                if self.ctx.lib:
                    return list(
                        toml_path.parent.joinpath(*["target", self.ctx.profile]).glob(
                            "*.so"
                        )
                    )

                else:  # Looking for executables, which have no extension on linux
                    result_files = []
                    compile_dst = toml_path.parent.joinpath(
                        *["target", self.ctx.profile, "deps"]
                    )
                    for _, _, filenames in os.walk(compile_dst):
                        for file in filenames:
                            if "." not in file:
                                result_files.append(
                                    pathlib.Path(compile_dst) / str(file)
                                )
                        break
                    return list(result_files)

    def compile_remote_crate(
        self, crate: Crate, crate_transform: Optional[Callable] = None
    ):
        archive_path: Path = crate.download()
        extracted_location = extract_tarfile(archive_path)

        self.compile_examples(crate, crate.features)
        exit(1)

        # Crates can be transformed if needed for a specific compilation.
        # For example, hyper needs a modification when being compiled with musl, due to metadata clash
        # with tokio macros.
        if crate_transform:
            crate_transform(extracted_location)

        result = self.compile_crate(crate, extracted_location.joinpath("Cargo.toml"))

        if result is None or len(result) == 0:
            raise CompilationError

        for r in result:
            log.info(f"Compiled {str(r)}")

        return result

    def _compile_with_cargo(
        self,
        toml_path: Path,
        features: Optional[List[Text]] = (),
    ) -> bool:
        """
        This algorithm is very stupid.
        Attempts to compile crates with the maximum of features available.
        If compilation fails, remove a feature, and try again.
        """
        args = [
            "rustup",
            "run",
            self.tc.name,
            "cargo",
            "build",
        ]

        if self.ctx.lib:
            args.append("--lib")

        if self.ctx.profile == "release":
            args.append("--release")

        if features:
            args.append("--features")
            args.append(
                ",".join(
                    list(filter(lambda f: f not in ["nightly", "default"], features))
                )
            )

        # Custom environ setup
        env = os.environ.copy()
        if self.ctx.env:
            for key, val in self.ctx.env.items():
                env[key] = val

        log.debug(f'{" ".join(args)} || With env : {self.ctx.env}')

        ret = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=toml_path.parent,
            env=env,
        )
        # print(ret.stderr)
        # print(ret.stdout)

        if ret.returncode == 0:
            return True

        if features:  # Remaining features to test compilation with
            # Removing one feature and try to compile again
            log.debug(f"Compilation failed, retrying with features : {features[1:]}")
            return self._compile_with_cargo(toml_path, features[1:])

        return False
