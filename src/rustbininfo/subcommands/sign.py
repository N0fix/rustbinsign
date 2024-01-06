import pathlib
import tarfile
from typing import List

from ..compilation import compile_crate
from ..info_gathering import get_dependencies, get_rustc_version
from ..model import Crate
from ..sig_providers.provider_base import BaseSigProvider
from ..signature_generation import Toolchain


def _download_deps(dependencies: List[Crate]):
    for dep in dependencies:
        yield dep, dep.download()


def _extract_crate(crate_path: pathlib.Path):
    assert crate_path.exists()

    tar = tarfile.open(crate_path)
    tar.extractall(path=crate_path.parent)
    tar.close()


def sign_libs(
    provider: BaseSigProvider, libs: List[pathlib.Path], signature_name: str
) -> pathlib.Path:
    return provider.generate_signature(libs, signature_name)


def sign_subcommand(
    provider: BaseSigProvider, target: pathlib.Path, signature_name: str
):
    if not target.exists():
        print(f"{target} do not exists")
        exit(1)

    print("Getting dependencies...")
    dependencies: List[Crate] = get_dependencies(target)
    _, version = get_rustc_version(target)
    tc = Toolchain(version).install()

    libs = tc.libs
    for dep, downloaded_path in _download_deps(dependencies):
        _extract_crate(downloaded_path)
        extracted_location = pathlib.Path(downloaded_path.parent) / str(
            downloaded_path.with_suffix("").with_suffix("")
        )

        try:
            print(extracted_location.joinpath("Cargo.toml"))
            result = compile_crate(
                dep, extracted_location.joinpath("Cargo.toml"), version
            )
            print(f"->>>>", result)
            for r in result:
                print(f"Compiled {str(r)}")

            libs += result

        except Exception as exc:
            print(exc)

    print(f"Generated : {provider.generate_signature(libs, signature_name)}")
