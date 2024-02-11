import json
import logging
import pathlib
import sys
import tarfile
from argparse import (ArgumentDefaultsHelpFormatter, ArgumentParser,
                      RawDescriptionHelpFormatter)
from enum import Enum
from typing import List

from rich import print

from .info_gathering import TargetRustInfo, get_dependencies, get_rustc_version
from .logger import get_log_handler, logger
from .model import CompilationCtx, Config, Crate
from .rustup import get_rustup_home
from .sig_providers.ida.ida import IDAProvider
from .sig_providers.ida.model import ConfigIDA
from .subcommands.download import download_subcommand
from .subcommands.info import info_subcommand
from .subcommands.sign import sign_libs, sign_subcommand
from .toolchain import ToolchainFactory
from .util import slugify

DESCRIPTION = """This script aims at facilitate creation of signatures for rust executables. It can detect dependencies and rustc version used in a target, and create signatures using a signature provider."""

example_text = r"""Usage examples:

 rustbininfo -l DEBUG info 'challenge.exe'
 rustbininfo download_sign IDA 'C:\Program Files\IDA Pro\idat64.exe' .\sigmake.exe hyper-0.14.27 1.70.0-x86_64-unknown-linux-gnu
 rustbininfo download hyper-0.14.27
 rustbininfo sign_stdlib --template ./profiles/ivanti_rust_sample.json -t 1.70.0-x86_64-unknown-linux-musl IDA ~/idat64 ~/sigmake
 rustbininfo get_std_lib 1.70.0-x86_64-unknown-linux-musl
 rustbininfo sign_libs -l .\sha2-0.10.8\target\release\sha2.lib -l .\crypt-0.4.2\target\release\crypt.lib IDA 'C:\Program Files\IDA Pro\idat64.exe' .\sigmake.exe
 rustbininfo sign_target -t 1.70.0-x86_64-unknown-linux-musl  --target ~/Downloads/target --no-std --signature_name malware_1.70.0_musl
 """


def parse_args():
    ## Provider subparsers
    provider = ArgumentParser(add_help=False)

    sig_subparsers = provider.add_subparsers(
        dest="provider",
        title="Available signature providers",
    )

    ida_parser = sig_subparsers.add_parser("IDA")
    ida_parser.add_argument("idat_path", type=pathlib.Path)
    ida_parser.add_argument("sigmake_path", type=pathlib.Path)

    toolchain_name_parser = ArgumentParser(add_help=False)
    toolchain_name_parser.add_argument(
        "-t",
        "--toolchain",
        type=str,
        default=None,
        dest="toolchain",
        help="Specific toolchain to use (optional). Use target triple.",
        required=False,
    )

    profile_parser = ArgumentParser(add_help=False)
    profile_parser.add_argument(
        "-p",
        "--profile",
        type=str,
        choices=["release", "debug"],
        default="release",
        dest="profile",
        help="Choose specific profile (default is release)",
        required=False,
    )

    template_parser = ArgumentParser(add_help=False)
    template_parser.add_argument(
        "--template",
        type=str,
        dest="template",
        help="Give a JSON file of the TOML modifications to operate before compilation.",
        required=False,
    )

    ## Main parser
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=RawDescriptionHelpFormatter,
        epilog=example_text,
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
    download_sign_parser = subparsers.add_parser(
        "download_sign",
        help="Download a crate. And signs it. Exemple: rand_chacha-0.3.1",
        parents=[provider, profile_parser, template_parser],
    )
    sign_stdlib_parser = subparsers.add_parser(
        "sign_stdlib",
        help="Sign standard lib toolchain",
        parents=[provider, template_parser, profile_parser],
    )
    signature_parser = subparsers.add_parser(
        "sign_target",
        help="Generate a signature for a given executable, using choosed signature provider",
        parents=[
            provider,
            toolchain_name_parser,
            profile_parser,
            template_parser,
        ],
    )
    signature_lib_parser = subparsers.add_parser(
        "sign_libs",
        help="Generate a signature for a given list of libs, using choosed signature provider",
        parents=[provider],
    )
    std_parser = subparsers.add_parser(
        "get_std_lib",
        parents=[profile_parser, template_parser],
        help="Download stdlib with symbols for a specific version of rustc",
    )

    info_parser.add_argument("target", type=pathlib.Path)

    sign_stdlib_parser.add_argument(
        "-t",
        "--toolchain",
        type=str,
        dest="toolchain",
        help="Toolchain version to sign",
        required=True,
    )

    download_parser.add_argument("crate")
    download_parser.add_argument("--directory", required=False, default=None)

    download_sign_parser.add_argument("crate")
    download_sign_parser.add_argument(
        "toolchain",
        type=str,
        help="Specific toolchain to use",
    )
    download_sign_parser.add_argument("--directory", required=False, default=None)

    signature_parser.add_argument("--target", type=pathlib.Path, required=True)
    signature_parser.add_argument("--signature_name", required=True)
    signature_parser.add_argument(
        "--no-std",
        help="Don't sign std lib",
        dest="no_std",
        action="store_true",
        default=False,
    )

    signature_lib_parser.add_argument(
        "--lib", "-l", action="append", type=pathlib.Path, required=True
    )

    std_parser.add_argument("toolchain", help="Specific toolchain. Use target triple.")

    return parser


def main_cli():
    parser = parse_args()
    args = parser.parse_args()
    provider = None
    template = None

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.logLevel:
        logger.setLevel(getattr(logging, args.logLevel))
        logger.addHandler(get_log_handler())

    if args.mode in ("download_sign", "sign_libs", "sign_target", "sign_stdlib"):
        if args.provider == "IDA":
            provider = IDAProvider(
                ConfigIDA(
                    idat=args.idat_path,
                    sigmake=args.sigmake_path,
                )
            )

        else:
            NotImplementedError(f"Provider {args.provider} do not exists")

    if args.mode in ("sign_stdlib", "download_sign", "sign_target"):
        if args.template:
            template = json.load(open(args.template, "r", encoding="utf-8"))

    if args.mode in ("download_sign", "sign_target", "sign_stdlib", "get_std_lib"):
        tc = (
            ToolchainFactory.from_target_triplet(args.toolchain)
            .set_compilation_profile(args.profile)
            .set_compilation_template(template)
        )
        if args.mode != "sign_target":
            tc.install()

    match args.mode:
        case "info":
            print(TargetRustInfo.from_target(args.target))

        case "download":
            download_subcommand(args.crate, args.directory)

        case "download_sign":
            libs = tc.compile_crate(Crate.from_depstring(args.crate))
            signature_path = sign_libs(provider, libs, "tmp")
            print(f"Generated signature : {signature_path}")

        case "sign_libs":
            signature_path = sign_libs(provider, args.lib, "tmp")
            print(f"Generated signature : {signature_path}")

        case "sign_target":
            if not args.toolchain:
                _, version = get_rustc_version(pathlib.Path(args.target))
                tc = (
                    ToolchainFactory.from_version(version)
                    .set_compilation_profile(args.profile)
                    .set_compilation_template(template)
                    .install()
                )

            sign_subcommand(
                provider,
                pathlib.Path(args.target),
                args.signature_name,
                tc,
                args.profile,
                not args.no_std,
                template,
            )

        case "sign_stdlib":
            template = template or "default"
            signame = f"{tc.name}-{args.profile}-{slugify(template)}"
            sign_libs(
                provider,
                tc.get_libs(),
                signame
            )
            print(f"Generated : {signame}.sig")

        case "get_std_lib":
            for lib in tc.get_libs():
                print(lib)


if __name__ == "__main__":
    main_cli()
