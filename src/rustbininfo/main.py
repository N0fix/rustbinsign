import logging
import pathlib
import sys
import tarfile
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, RawDescriptionHelpFormatter
from typing import List
from rich import print

from .compilation import compile_crate
from .info_gathering import get_dependencies, get_rustc_version, TargetRustInfo
from .logger import get_log_handler, logger
from .model import Config, Crate
from .rustup import get_rustup_home
from .sig_providers.ida.ida import IDAProvider
from .sig_providers.ida.model import ConfigIDA
from .signature_generation import Toolchain
from .subcommands.download import download_subcommand
from .subcommands.info import info_subcommand
from .subcommands.sign import sign_libs, sign_subcommand

DESCRIPTION = """This script aims at facilitate creation of signatures for rust executables. It can detect dependencies and rustc version used in a target, and create signatures using a signature provider."""

example_text = r"""Usage examples:

 rustbininfo -l DEBUG info 'challenge.exe'
 rustbininfo sign_target --target challenge.exe --signature_name custom_sig IDA 'C:\Program Files\IDA Pro\idat64.exe' .\sigmake.exe
 rustbininfo sign_libs -l .\sha2-0.10.8\target\release\sha2.lib -l .\crypt-0.4.2\target\release\crypt.lib IDA 'C:\Program Files\IDA Pro\idat64.exe' .\sigmake.exe
"""

def parse_args():
    ## Provider subparsers
    provider = ArgumentParser(add_help=False)

    sig_subparsers = provider.add_subparsers(
        dest="provider", title="Available signature providers",
    )

    ida_parser = sig_subparsers.add_parser("IDA")
    ida_parser.add_argument("idat_path", type=pathlib.Path)
    # ida_parser.add_argument("pattern_generator", type=pathlib.Path, help="(pcf.exe, pelf...)")
    ida_parser.add_argument("sigmake_path", type=pathlib.Path)

    ## Main parser
    parser = ArgumentParser(
        description=DESCRIPTION, formatter_class=RawDescriptionHelpFormatter, epilog=example_text
    )

    parser.add_argument(
        "-l",
        "--log",
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )

    ## Subcommand parsers
    subparsers = parser.add_subparsers(dest="mode", title="mode", help="Mode to use")
    info_parser = subparsers.add_parser(
        "info", help="Get information about an executable"
    )
    download_parser = subparsers.add_parser(
        "download", help="Download a crate. Exemple: rand_chacha-0.3.1"
    )
    signature_parser = subparsers.add_parser(
        "sign_target",
        help="Generate a signature for a given executable, using choosed signature provider",
        parents=[provider],
    )
    signature_lib_parser = subparsers.add_parser(
        "sign_libs",
        help="Generate a signature for a given list of libs, using choosed signature provider",
        parents=[provider],
    )
    std_parser = subparsers.add_parser(
        "get_std_lib",
        help="Download stdlib with symbols for a specific version of rustc",
    )

    info_parser.add_argument("target", type=pathlib.Path)

    download_parser.add_argument("crate")
    download_parser.add_argument("--directory", required=False, default=None)

    signature_parser.add_argument("--target", type=pathlib.Path, required=True)
    signature_parser.add_argument("--signature_name", required=True)

    signature_lib_parser.add_argument(
        "--lib", "-l", action="append", type=pathlib.Path, required=True
    )

    std_parser.add_argument("toolchain_version")

    return parser


def generate_sig(rustc_version: str, cfg: Config):
    tc = Toolchain(rustc_version, cfg)
    tc.install()
    pattern_file_list = tc.generate_pattern_files(tc.libs)
    signame = tc.build_sig(pattern_file_list, cfg)

    print(f"Generated {str(pathlib.Path(signame).absolute())}")


def main_cli():
    parser = parse_args()
    # print(parser)
    args = parser.parse_args()
    # print(args)
    provider = None

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.logLevel:
        logger.setLevel(getattr(logging, args.logLevel))
        logger.addHandler(get_log_handler())

    if args.mode in ("sign_libs", "sign_target"):
        if args.provider == "IDA":
            provider = IDAProvider(
                ConfigIDA(
                    idat=args.idat_path,
                    # pattern_generator=args.pattern_generator,
                    sigmake=args.sigmake_path,
                )
            )

        else:
            NotImplementedError(f"Provider {args.provider} do not exists")

    if args.mode == "info":
        # print(TargetRustInfo.from_target(args.target))
        info_subcommand(pathlib.Path(args.target))

    elif args.mode == "download":
        download_subcommand(args.crate)

    elif args.mode == "sign_libs":
        signature_path = sign_libs(provider, args.lib, "tmp")
        print(f"Generated signature : {signature_path}")

    elif args.mode == "sign_target":
        sign_subcommand(provider, pathlib.Path(args.target), args.signature_name)

    elif args.mode == "get_std_lib":
        tc = Toolchain(args.toolchain_version).install()
        for lib in tc.libs:
            print(lib)


if __name__ == "__main__":
    main_cli()
