import pathlib
from typing import List, Optional

from ..info_gathering import get_dependencies
from ..logger import logger as log
from ..model import CompilationCtx, Crate
from ..sig_providers.provider_base import BaseSigProvider
from ..toolchains.model import ToolchainModel


def sign_libs(
    provider: BaseSigProvider, libs: List[pathlib.Path], signature_name: str
) -> pathlib.Path:
    return provider.generate_signature(libs, signature_name)


def sign_subcommand(
    provider: BaseSigProvider,
    target: pathlib.Path,
    signature_name: str,
    toolchain: ToolchainModel,
    profile: Optional[str] = "release",
    sign_std: bool = True,
    template: Optional[pathlib.Path] = None,
):
    if profile is None:
        profile = "release"

    if not target.exists():
        print(f"{target} do not exists")
        exit(1)

    log.info("Getting dependencies...")
    dependencies: List[Crate] = get_dependencies(target)
    # _, version = get_rustc_version(target)
    tc = toolchain.install()
    failed = []
    if sign_std:
        libs = tc.get_libs()

    else:
        libs = []

    for dep in dependencies:
        try:
            args = {"profile": "release"}
            if template is not None:
                args["template"] = template

            libs += toolchain.compile_crate(dep, CompilationCtx(**args))

        except Exception as exc:
            failed.append(dep.name)
            print(exc)

    print("Failed to compile :")
    for fail in failed:
        print(f"\t{fail}")
    print(f"Generated : {provider.generate_signature(libs, signature_name)}")
