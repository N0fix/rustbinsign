import json
import logging
import pathlib
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from rich import print
from rustbininfo import Crate, TargetRustInfo, get_min_max_update_time, get_rustc_version

from .logger import get_log_handler, logger
from .sig_providers.ida.ida import IDAProvider
from .sig_providers.python.model import ConfigPython
from .sig_providers.python.provider import PythonProvider
from .subcommands.download import download_subcommand
from .subcommands.sign import compile_target_subcommand, sign_libs, sign_subcommand
from .toolchain import ToolchainFactory
from .util import slugify

DESCRIPTION = """This script aims at facilitate creation of signatures for rust executables. It can detect dependencies and rustc version used in a target, and create signatures using a signature provider."""

example_text = r"""Usage examples:

 rustbinsign -l DEBUG info 'challenge.exe'
 rustbinsign -l DEBUG download_sign --provider IDA hyper-0.14.27 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign -l DEBUG download hyper-0.14.27
 rustbinsign -l DEBUG download_compile rand_chacha-0.3.1 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign -l DEBUG compile --template ./profile/ctf.json /tmp/rustbininfo/rand_chacha-0.3.1/Cargo.toml 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign -l DEBUG sign_stdlib --template ./profiles/ivanti_rust_sample.json -t 1.70.0-x86_64-unknown-linux-musl --provider IDA
 rustbinsign -l DEBUG get_std_lib 1.70.0-x86_64-unknown-linux-musl
 rustbinsign -l DEBUG sign_libs -l .\sha2-0.10.8\target\release\sha2.lib -l .\crypt-0.4.2\target\release\crypt.lib --provider IDA
 rustbinsign -l DEBUG sign_target -t stable-x86_64-pc-windows-gnu --template ./profiles/target.json  --provider IDA --target ./target.exe --no-std --signature_name target_sig
 """


def parse_args():
    ## Provider subparsers
    provider = ArgumentParser(add_help=False)
    provider.add_argument(
        "--provider",
        type=str,
        choices=["IDA", "Python"],
        default="Python",
        dest="provider",
        help="Signature provider. This is the tool that will be used to create signatures.",
    )

    signature_name_parser = ArgumentParser(add_help=False)
    signature_name_parser.add_argument(
        "--signature-name",
        default="signature_output",
        type=str,
        help="Name of the signature to produce",
    )

    full_compilation = ArgumentParser(add_help=False)
    full_compilation.add_argument(
        "-f",
        "--full-compilation",
        default=False,
        action="store_true",
        help="Tries to compile with tests, benches and examples, to maximize code coverage. Gives the best results, but takes a long time !",
    )

    toolchain_name_parser = ArgumentParser(add_help=False)
    toolchain_name_parser.add_argument(
        "-t",
        "--toolchain",
        type=str,
        default=None,
        dest="toolchain",
        help="Specific toolchain to use. Use target triple with version (e.g 1.70.0-x86_64-unknown-linux-musl)",
        required=True,
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

    compile_with_all_parser = ArgumentParser(add_help=False)
    compile_with_all_parser.add_argument(
        "-a",
        "--all",
        required=False,
        action="store_true",
        help="Compiles examples, benches and tests. Default to False.",
        dest="compile_all",
        default=False,
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
        default="INFO",
    )

    ## Subcommand parsers
    subparsers = parser.add_subparsers(dest="mode", title="mode", help="Mode to use")

    ## INFO
    info_parser = subparsers.add_parser("info", help="Get information about an executable")

    ## DOWNLOAD
    download_parser = subparsers.add_parser("download", help="Download a crate. Exemple: rand_chacha-0.3.1")
    download_sign_parser = subparsers.add_parser(
        "download_sign",
        help="Download a crate and signs it. Exemple: rand_chacha-0.3.1",
        parents=[provider, signature_name_parser, profile_parser, template_parser, full_compilation],
    )

    download_compile_parser = subparsers.add_parser(
        "download_compile",
        parents=[
            compile_with_all_parser,
            profile_parser,
            template_parser,
            full_compilation,
        ],
        help="Download a crate and compiles it. Exemple: rand_chacha-0.3.1",
    )

    ## COMPILE
    compile_parser = subparsers.add_parser(
        "compile",
        help="Compiles a crate. Exemple: rand_chacha-0.3.1",
        parents=[
            compile_with_all_parser,
            profile_parser,
            template_parser,
            full_compilation,
        ],
    )

    compile_target_parser = subparsers.add_parser(
        "compile_target",
        help="Compiles all dependencies detected in target compiled rust executable.",
        parents=[
            toolchain_name_parser,
            compile_with_all_parser,
            profile_parser,
            template_parser,
            full_compilation,
        ],
    )

    ## SIGN
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
            signature_name_parser,
            toolchain_name_parser,
            profile_parser,
            template_parser,
            full_compilation,
        ],
    )
    signature_lib_parser = subparsers.add_parser(
        "sign_libs",
        help="Generate a signature for a given list of libs, using choosed signature provider",
        parents=[provider, signature_name_parser],
    )
    std_parser = subparsers.add_parser(
        "get_std_lib",
        parents=[profile_parser, template_parser],
        help="Download stdlib with symbols for a specific version of rustc",
    )

    ## DETAILS OF SUBCOMMANDS

    info_parser.add_argument("target", type=pathlib.Path)
    info_parser.add_argument("-f", "--full", action="store_true", default=False)

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

    compile_parser.add_argument("toml_path")
    compile_parser.add_argument("toolchain")

    compile_target_parser.add_argument("target")

    download_sign_parser.add_argument("crate")
    download_sign_parser.add_argument(
        "toolchain",
        type=str,
        help="Specific toolchain to use",
    )

    download_compile_parser.add_argument("crate")
    download_compile_parser.add_argument(
        "toolchain",
        type=str,
        help="Specific toolchain to use",
    )

    signature_parser.add_argument("--target", type=pathlib.Path, required=True)

    signature_parser.add_argument(
        "--no-std",
        help="Don't sign std lib",
        dest="no_std",
        action="store_true",
        default=False,
    )

    signature_lib_parser.add_argument("--lib", "-l", action="append", type=pathlib.Path, required=True)

    std_parser.add_argument("toolchain", help="Specific toolchain. Use target triple.")

    compiletime_parser = subparsers.add_parser(
        "guess_project_creation_timestamp",
        help="Tries to guess the compilation date based on dependencies version",
    )
    compiletime_parser.add_argument("target", type=pathlib.Path)

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
            provider = IDAProvider()

        else:
            provider = PythonProvider(ConfigPython(target=args.target))
            # NotImplementedError(f"Provider {args.provider} do not exists")

    if args.mode in (
        "compile",
        "compile_target",
        "sign_stdlib",
        "download_compile",
        "download_sign",
        "sign_target",
    ):
        if args.template:
            template = json.load(open(args.template, "r", encoding="utf-8"))

    if args.mode in (
        "compile",
        "compile_target",
        "download_sign",
        "download_compile",
        "sign_target",
        "sign_stdlib",
        "get_std_lib",
    ):
        tc = (
            ToolchainFactory.from_target_triplet(args.toolchain)
            .set_compilation_profile(args.profile)
            .set_compilation_template(template)
            .install()
        )

    match args.mode:
        case "info":
            print(TargetRustInfo.from_target(args.target, not args.full))

        case "download":
            download_subcommand(args.crate, args.directory)

        case "compile":
            libs = tc.compile_crate(
                crate=Crate.from_toml(args.toml_path, fast_load=False),
                toml_path=pathlib.Path(args.toml_path),
                compile_all=args.full_compilation,
            )
            [print(lib) for lib in libs]

        case "compile_target":
            if not args.toolchain:
                _, version = get_rustc_version(pathlib.Path(args.target))
                tc = (
                    ToolchainFactory.from_version(version)
                    .set_compilation_profile(args.profile)
                    .set_compilation_template(template)
                    .install()
                )

            libs, fails = compile_target_subcommand(
                pathlib.Path(args.target),
                tc,
                args.profile,
                template,
                compile_all=args.full_compilation,
            )
            [print(lib) for lib in libs]
            [print(f"Failed to compile: {fail}", file=sys.stderr) for fail in fails]

        case "download_sign":
            libs = tc.compile_crate(crate=Crate.from_depstring(args.crate), compile_all=args.full_compilation)
            signature_path = sign_libs(provider, libs, args.signature_name)
            print(f"Generated signature : {signature_path}")

        case "download_compile":
            libs = tc.compile_crate(
                crate=Crate.from_depstring(args.crate),
                compile_all=args.full_compilation,
            )
            [print(lib) for lib in libs]

        case "sign_libs":
            signature_path = sign_libs(provider, args.lib, args.signature_name)
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
                compile_all=args.full_compilation,
            )

        case "sign_stdlib":
            template = template or "default"
            signame = f"{tc.name}-{args.profile}-{slugify(template)}"
            sign_libs(provider, tc.get_libs(), signame)
            print(f"Generated : {signame}.sig")

        case "get_std_lib":
            for lib in tc.get_libs():
                print(lib)

        case "guess_project_creation_timestamp":
            ti = TargetRustInfo.from_target(args.target)
            min_date, max_date = get_min_max_update_time(ti.dependencies)
            print(f"Latest dependency was added between {min_date} and {max_date}")


if __name__ == "__main__":
    main_cli()
