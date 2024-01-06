import logging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from pathlib import Path

from rustbininfo import ConfigIDA, IDAProvider, Toolchain, sign_libs


def parse_args() -> Namespace:
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-l",
        "--log",
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )

    parser.add_argument("tags_list")
    return parser.parse_args()


def get_libs(tag: str):
    tc = Toolchain(tag).install()
    return [Path(l) for l in tc.libs]


def generate_sig(libs, name):
    provider = IDAProvider(
        ConfigIDA(
            idat="/home/nofix/idapro-8.2/idat64",
            sigmake="/home/nofix/git/IDA/training/idasdk+tools/flair83/bin/linux/sigmake",
        )
    )
    signature_path = sign_libs(provider, libs, f"rust-std-{name}-linux-gnu")
    print(f"Generated signature : {signature_path}")


if __name__ == "__main__":
    args: Namespace = parse_args()
    lines = open(args.tags_list, "r", encoding="utf-8").readlines()
    for tag in lines:
        tag = tag.strip()
        libs = get_libs(tag)
        generate_sig(libs, tag)
