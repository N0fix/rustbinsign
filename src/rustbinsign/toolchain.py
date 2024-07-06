import semver

from .exceptions import InvalidVersionError
from .logger import logger as log


class ToolchainFactory:
    @classmethod
    def from_target_triplet(cls, name: str):
        """
        Usage example:
        >>> ToolchainFactory.from_target_triplet("1.70.0-x86_64-unknown-linux-gnu")

        Args:
            name (str) : Target triplet requiered

        Returns:
            Toolchain
        """
        from .toolchains import (
            DefaultToolchain,
            MinGWToolchain,
            MuslToolchain,
            MuslToolchain_x86,
        )

        TOOLCHAINS = [MuslToolchain, MuslToolchain_x86, MinGWToolchain]

        try:
            version, tc_name = name.split("-", 1)

            if version not in ("stable", "nightly"):
                try:
                    semver.Version.parse(version)

                except Exception as exc:
                    raise InvalidVersionError from exc

            for toolchain in TOOLCHAINS:
                if toolchain.match_toolchain(tc_name):
                    return toolchain(version, tc_name)

            return DefaultToolchain(version, tc_name)

        except:
            log.error(f"Invalid toolchain name triplet {name}")
            exit(1)

    @classmethod
    def from_version(cls, version: str):
        from .toolchains import DefaultToolchain

        return DefaultToolchain(version)
