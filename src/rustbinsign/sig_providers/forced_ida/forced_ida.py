import os
import pathlib
import subprocess
import sys
import tempfile

from ...logger import logger as log
from ..ida.ida import IDAProvider


class ForcedIDAProvider(IDAProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import shutil
        ida_makesig_plugin_path = pathlib.Path(shutil.which("idat64")).parent / "plugins" / "makesig64_patched.so"
        if not ida_makesig_plugin_path.exists():
            print("Please patch the ida makesig plugin before using forcedIDA provider.", file=sys.stderr)
            exit(1)

    def _generate_pattern(self, libfile) -> pathlib.Path:
        assert libfile.exists()
        log.debug(f"Gen for {libfile}...")
        script_path = pathlib.Path(__file__).parent.resolve().joinpath("sig_gen.py")
        target_path = pathlib.Path(libfile).with_suffix(".pat")

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
