import pathlib

import toml
from ....logger import logger as log


def transform(crate_path: pathlib.Path):
    # [dev-dependencies.tokio]
    # version = "1"
    # features = [ "fs", "macros", "io-std", "io-util", "rt", "rt-multi-thread", "sync", "time", "test-util",]

    log.info(f"Applying transform on crate Hyper ({crate_path})")
    toml_path = crate_path.joinpath("Cargo.toml")
    crate_toml = toml.load(toml_path)
    idx = crate_toml["dev-dependencies"]["tokio"]["features"].index("macros")
    del crate_toml["dev-dependencies"]["tokio"]["features"][idx]
    toml.dump(crate_toml, open(toml_path, "w", encoding="utf-8"))
