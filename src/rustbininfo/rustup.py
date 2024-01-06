import shlex
import subprocess


def install_toolchain(rustc_version: str):
    subprocess.run(
        shlex.split(f"rustup install {rustc_version} --profile minimal"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        shlex.split(f"rustup component add rustc-dev --toolchain {rustc_version}"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_rustup_home():
    return subprocess.check_output(shlex.split("rustup show home")).decode().strip()
