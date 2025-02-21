import json
import pathlib

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from datasketch.minhash import MinHash
from pydantic import BaseModel, Extra
from smda.common import SmdaFunction
from smda.Disassembler import Disassembler

from ...logger import logger as log
from ..provider_base import BaseSigProvider
from .model import ConfigPython

cache_opts = {"cache.type": "file", "cache.data_dir": "/tmp/cache/data", "cache.lock_dir": "/tmp/cache/lock"}

cache = CacheManager(**parse_cache_config_options(cache_opts))


class PythonProviderFunction(BaseModel, extra="allow"):
    name: str | None
    code: str
    offset: int

    def minhash(self) -> MinHash:
        if getattr(self, "_minhash_value", None) is None:
            chunks = [self.code[i : i + 2] for i in range(0, len(self.code), 2)]
            m2 = MinHash()
            for data in chunks:
                m2.update(data.encode())

            self._minhash_value = m2

        return self._minhash_value


class PythonProviderResult(BaseModel):
    lib_name: str
    functions: list[PythonProviderFunction]


class Libs(BaseModel):
    libs: list[PythonProviderResult]


class PythonProvider(BaseSigProvider):
    cfg: ConfigPython

    def __init__(self, cfg: ConfigPython):
        if cfg is None:
            self.cfg = ConfigPython()

        else:
            self.cfg = cfg

    def generate_signature(self, libs: list[pathlib.Path], sig_name: str | None) -> pathlib.Path:
        results: list[PythonProviderResult] = []
        for lib in libs:
            log.info(f"Signing {lib}")
            r = self._get_lib_functions_hashes(lib)
            results.append(PythonProviderResult(lib_name=lib.name, functions=r))

        l = Libs(libs=results)
        output_file = pathlib.Path(sig_name)
        output_file.write_text(l.model_dump_json(indent=4))
        # exit(1)
        if self.cfg.target:
            target: list[PythonProviderFunction] = self._get_lib_functions_hashes(self.cfg.target)
            from rich.progress import track

            for fn in track(target):
                m1 = fn.minhash()

                for res in results:
                    for result_function in res.functions:
                        if not result_function.name:
                            continue
                        if result_function.minhash().jaccard(m1) > 0.9:
                            print(hex(fn.offset), result_function.name)

    def _hash_fn(self, fn: SmdaFunction):
        code = ""
        for ins in fn.getInstructions():
            off = ins.detailed.disp
            if (
                ins.mnemonic
                in [
                    "call",
                    "ja",
                    "jae",
                    "jb",
                    "jbe",
                    "jcxz",
                    "je",
                    "jecxz",
                    "jg",
                    "jge",
                    "jl",
                    "jle",
                    "jmp",
                    "jne",
                    "jno",
                    "jnp",
                    "jns",
                    "jo",
                    "jp",
                    "jrcxz",
                    "js",
                    "lcall",
                    "ljmp",
                ]
                or (off >= 0x1000)
                or (off < 0)
            ):
                code += ins.bytes[:2] + "00"

            else:
                code += ins.bytes

        return code

    @cache.cache(expire=3600)
    def _get_lib_functions_hashes(self, lib: pathlib.Path) -> list[PythonProviderFunction]:
        d = Disassembler()
        report = d.disassembleFile(lib)
        result: list[PythonProviderFunction] = []
        for fn in report.getFunctions():
            code = self._hash_fn(fn)
            if len(code) > 20:
                result.append(PythonProviderFunction(name=fn.function_name, code=code, offset=fn.offset))

        return result
