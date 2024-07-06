import pathlib
from typing import List, Optional, Tuple

from rustbininfo import Crate, TargetRustInfo

from ..logger import logger as log
from ..model import CompilationCtx
from ..sig_providers.provider_base import BaseSigProvider
from ..toolchains.model import ToolchainModel


def sign_libs(
    provider: BaseSigProvider, libs: List[pathlib.Path], signature_name: str
) -> pathlib.Path:
    return provider.generate_signature(libs, signature_name)


def compile_target_subcommand(
    target: pathlib.Path,
    toolchain: ToolchainModel,
    profile: Optional[str] = "release",
    template: Optional[pathlib.Path] = None,
) -> Tuple[List, List]:
    if profile is None:
        profile = "release"

    if not target.exists():
        print(f"{target} do not exists")
        exit(1)

    log.info("Getting dependencies...")

    dependencies: List[Crate] = TargetRustInfo.from_target(target).dependencies
    # _, version = get_rustc_version(target)
    # tc = toolchain.install()
    failed = []
    # if sign_std:
    # libs = tc.get_libs()

    # else:
    libs = []

    for dep in dependencies:
        try:
            args = {"profile": profile}
            if template is not None:
                args["template"] = template
            libs += toolchain.compile_crate(crate=dep, ctx=CompilationCtx(**args))

        except Exception as exc:
            failed.append(dep.name)
            log.error(exc)

    return libs, failed


def sign_subcommand(
    provider: BaseSigProvider,
    target: pathlib.Path,
    signature_name: str,
    toolchain: ToolchainModel,
    profile: Optional[str] = "release",
    sign_std: bool = True,
    template: Optional[pathlib.Path] = None,
):
    libs, fails = compile_target_subcommand(target, toolchain, profile, template)
    if sign_std:
        libs += toolchain.get_libs()

    if fails:
        print("Failed to compile :")
        for fail in failed:
            print(f"\t{fail}")

    print(f"Generated : {provider.generate_signature(libs, signature_name)}")
