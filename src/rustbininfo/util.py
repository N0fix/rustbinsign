import pathlib
import tarfile
import tempfile


def get_default_dest_dir() -> pathlib.Path:
    destination_directory = pathlib.Path(tempfile.gettempdir()) / "ariane"
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
