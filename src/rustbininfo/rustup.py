import shlex
import subprocess
from typing import Optional
from .logger import logger as log


def rustup_install_toolchain(toolchain):
    log.warning(
        "Don't forget to install your toolchain first using 'rustup install {toolchain}'"
    )
    subprocess.run(
        shlex.split(f"rustup install {toolchain} --profile minimal"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        shlex.split(f"rustup component add rustc-dev --toolchain {toolchain}"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_rustup_home():
    return subprocess.check_output(shlex.split("rustup show home")).decode().strip()
