import pathlib
import re
import tarfile
import tempfile
import unicodedata


def get_default_dest_dir() -> pathlib.Path:
    destination_directory = pathlib.Path(tempfile.gettempdir()) / __package__
    destination_directory.mkdir(exist_ok=True)
    return destination_directory


def extract_tarfile(tar_path: pathlib.Path):
    assert tar_path.exists()

    tar = tarfile.open(tar_path)
    tar.extractall(path=tar_path.parent)
    tar.close()

    if ".gz" in tar_path.suffixes:
        tar_path = tar_path.with_suffix("")

    if ".tar" in tar_path.suffixes:
        tar_path = tar_path.with_suffix("")

    if ".tgz" in tar_path.suffixes:
        tar_path = tar_path.with_suffix("")

    return tar_path


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
