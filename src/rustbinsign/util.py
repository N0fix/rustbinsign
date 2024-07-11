import pathlib
import re
import tarfile
import tempfile
from typing import Optional
import unicodedata
import shutil

def get_default_dest_dir() -> pathlib.Path:
    destination_directory = pathlib.Path(tempfile.gettempdir()) / __package__
    destination_directory.mkdir(exist_ok=True)
    return destination_directory


def extract_tarfile(tar_path: pathlib.Path) -> pathlib.Path:
    """Should only be used on crates.io downloaded crates

    Args:
        tar_path (pathlib.Path)

    Returns:
        pathlib.Path: directory with extracted content
    """
    assert tar_path.exists()

    tar = tarfile.open(tar_path)
    tar.extractall(path=tar_path.parent)
    members = tar.members
    assert len(members) != 0  # should contain content
    result_path = members[0].name.split("/")[0]
    tar.close()
    return pathlib.Path(tar_path.parent).joinpath(result_path)


# Taken from https://stackoverflow.com/a/295466
def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")

def get_installed_program_path(program: str) -> Optional[str]:
    return shutil.which(program)

def is_installed(program: str) -> bool:
    return get_installed_program_path(program) is not None
