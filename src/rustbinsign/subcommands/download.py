import pathlib
from typing import Optional

from rustbininfo import Crate


def download_subcommand(
    crate_name: str, dest_dir: Optional[str] = None
) -> pathlib.Path:
    c = Crate.from_depstring(crate_name)
    result = c.download(dest_dir)
    print(f"{c} downloaded to {result}")
    return pathlib.Path(result)
