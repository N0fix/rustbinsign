import shlex
import subprocess

from .logger import logger


def rustup_install_toolchain(version, toolchain_name):
    subprocess.run(
        shlex.split(f"rustup target add {toolchain_name}"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        shlex.split(f"rustup +{version} target add {toolchain_name}"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        shlex.split(f"rustup install {version}-{toolchain_name} --profile minimal"),
        # check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        subprocess.run(
            shlex.split(
                f"rustup component add rustc-dev --toolchain {version}-{toolchain_name}"
            ),
            # check=True,
            timeout=120,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    except subprocess.TimeoutExpired:
        logger.error(
            f"rustup component add rustc-dev --toolchain {version}-{toolchain_name} : STATUS [FAILED]"
        )


def get_rustup_home():
    return subprocess.check_output(shlex.split("rustup show home")).decode().strip()
