import multiprocessing
import os
import pathlib
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from multiprocessing.pool import ThreadPool

from parse import *

from ...logger import logger as log
from ..provider_base import BaseSigProvider
from .model import ConfigIDA


class SignatureError(Exception):
    def __init__(self, message="An error occured running IDA"):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


def _remove_line(filepath: pathlib.Path, line_number: int):
    assert isinstance(filepath, pathlib.Path)
    assert filepath.exists()

    # list to store file lines
    lines = []
    # read file
    with open(filepath, "r", encoding="utf-8") as fp:
        # read an store all lines into list
        lines = fp.readlines()

    # Write file
    with open(filepath, "w+", encoding="utf-8") as fp:
        # iterate each line
        for number, line in enumerate(lines):
            # delete line 5 and 8. or pass any Nth line you want to remove
            # note list index starts from 0
            if number != line_number:
                fp.write(line)


class IDAProvider(BaseSigProvider):
    cfg: ConfigIDA

    def __init__(self, cfg: Optional[ConfigIDA] = None):
        if cfg is None:
            self.cfg = ConfigIDA()

        else:
            self.cfg = cfg

    def generate_signature(
        self, libs: List[pathlib.Path], sig_name: Optional[str]
    ) -> pathlib.Path:
        POOL_SIZE = multiprocessing.cpu_count()
        log.info(f"Generating pattern files with {POOL_SIZE} threads...")
        pats = []
        futures = []
        fails = 0
        tp = ThreadPoolExecutor(max_workers=POOL_SIZE)

        def routine(self, lib):
            return self._generate_pattern(lib)

        for lib in libs:
            futures.append(tp.submit(routine, self, lib))

        for fut in futures:
            try:
                pats.append(fut.result())

            except Exception as exc:
                print(exc)
                fails += 1

        log.info(f"{len(pats)} pat generated. {fails} failed.")

        if sig_name is None:
            sig_name = f"rust-std-{self.version}-{os.name}"

        return self._generate_sig_file(pats, sig_name)

    def _run_sig(self, cmdline):
        log.debug(f'Running command: "{" ".join(cmdline)}"')
        p = subprocess.run(
            cmdline,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        if os.name != "nt":
            if b"Not enough bytes left" in p.stdout:
                filepath, line, _ = parse(
                    "{} ({}): FATAL: Not enough bytes left{}", p.stdout.decode()
                )
                log.warning(f"Pattern file {filepath} has an error line {line}")
                _remove_line(pathlib.Path(filepath), line)
                return self._run_sig(cmdline)

        if p.returncode != 0:
            print(p.stderr, sys.stderr)
            print(p.stdout, sys.stdout)
            raise SignatureError

    def _generate_single_sig(self, pat: pathlib.Path):
        assert isinstance(pat, pathlib.Path)
        cmdline = [
            f"{str(self.cfg.sigmake)}",
            "-t5",
            f'-n"{pat.name}"',
            "-s",
            f"{str(pat)}",
            f"{str(pat)}.sig",
        ]
        self._run_sig(cmdline)

    def _generate_single_sigs(self, pats: List[pathlib.Path]):
        with ThreadPool(10) as p:
            w = []
            for pat in pats:
                w.append(p.apply_async(self._generate_single_sig, args=(pat,)))
            [_.get() for _ in w]

    def _generate_sig_file(self, pats: List[pathlib.Path], sig_name):
        if len(pats) == 0:
            raise SignatureError("No pattern files found")

        self._generate_single_sigs(pats)

        cmdline = [f"{str(self.cfg.sigmake)}", "-t5", f'-n"{sig_name}"', "-s"]
        for pat in pats:
            cmdline.append(str(pat))
        cmdline.append(f"{sig_name}.sig")

        self._run_sig(cmdline)
        return f"{sig_name}.sig"

    def _generate_pattern(self, libfile) -> pathlib.Path:
        assert libfile.exists()
        log.debug(f"Gen for {libfile}...")
        script_path = pathlib.Path(__file__).parent.resolve().joinpath("idb2pat.py")
        target_path = (
            pathlib.Path(os.getcwd()).joinpath(libfile.name).with_suffix(".pat")
        )

        if target_path.exists():  # Don't resign if signed already
            return target_path

        assert script_path.exists()
        if os.name != "nt":
            script_cmd = f'-S{script_path} "{str(target_path)}"'

        else:
            script_cmd = f"-S{script_path} {str(target_path)}"
        env = os.environ
        env["TVHEADLESS"] = "1"  # requiered for IDAt linux
        env["IDALOG"] = str(pathlib.Path(tempfile.gettempdir(), "idalog.txt"))
        env["TERM"] = "xterm"
        args = [
            f"{self.cfg.idat}",
            script_cmd,
            "-a",
            "-A",
            f"{str(libfile)}",
        ]

        # log.debug(" ".join(args))

        subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            check=True,
            # shell=True,
            env=env,
        )
        log.debug(f"Saved pat file to {target_path}")
        return target_path

    def _generate_pattern_files(self, libs) -> List[pathlib.Path]:
        return [self._generate_pattern(lib) for lib in libs]
