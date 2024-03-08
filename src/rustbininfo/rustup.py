import shlex
import subprocess


def rustup_install_toolchain(version, toolchain_name):
    subprocess.run(
        shlex.split(f"rustup target add {toolchain_name}"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        shlex.split(f"rustup install {version}-{toolchain_name} --profile minimal"),
        # check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        shlex.split(f"rustup component add rustc-dev --toolchain {version}-{toolchain_name}"),
        # check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_rustup_home():
    return subprocess.check_output(shlex.split("rustup show home")).decode().strip()
