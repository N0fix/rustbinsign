from typing import Optional

from ..model import Crate


def download_subcommand(crate_name: str, dest_dir: Optional[str] = None):
    c = Crate.from_depstring(crate_name)
    result = c.download(dest_dir)
    print(f"{c} downloaded to {result}")
