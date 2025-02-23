import json
import pathlib

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from datasketch.minhash import MinHash
from pydantic import BaseModel
from rich.progress import track
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

    def _filter_results(self):
        l = Libs(libs=[])
        names = set()
        for res in self.libs:
            f = []
            for func in res.functions:
                if not func.name or func.name in names:
                    continue

                names.add(func.name)
                f.append(func)

            l.libs.append(PythonProviderResult(lib_name=res.lib_name, functions=f))

        return l

    def get_nb_of_fns(self):
        s = 0
        for res in self.libs:
            s = sum([s, len(res.functions)])

        return s


class PythonProvider(BaseSigProvider):
    cfg: ConfigPython

    def __init__(self, cfg: ConfigPython):
        if cfg is None:
            self.cfg = ConfigPython()

        else:
            self.cfg = cfg

    def generate_signature(self, libs: list[pathlib.Path], sig_name: str | None) -> pathlib.Path:
        results: list[PythonProviderResult] = []
        for lib in track(libs):
            log.info(f"Signing {lib}")
            r = self._get_lib_functions_hashes(lib)
            nb_of_fns = len(list(filter(None, [f.name for f in r])))
            if nb_of_fns <= 1:
                log.warning(f"No function found in {lib}")
            results.append(PythonProviderResult(lib_name=lib.name, functions=r))

        l = Libs(libs=results)
        l = l._filter_results()
        output_file = pathlib.Path("/tmp/x.json")
        output_file.write_text(l.model_dump_json(indent=4))
        print(f"Calculating signature hashes for {l.get_nb_of_fns()} functions")
        similarity_results = {}

        if self.cfg.target:
            target: list[PythonProviderFunction] = self._get_lib_functions_hashes(self.cfg.target)

            for fn in track(list(target)):
                m1 = fn.minhash()

                for res in l.libs:
                    for result_function in res.functions:
                        if not result_function.name:
                            continue

                        similarity = result_function.minhash().jaccard(m1)
                        if similarity > 0.9:
                            print(hex(fn.offset), result_function.name, similarity)
                            tupl = similarity_results.get(fn.offset, None)
                            if tupl is None:
                                similarity_results[fn.offset] = (similarity, result_function.name)

                            # (similarity, result_function.name))
                            if similarity_results[fn.offset][0] < similarity:
                                similarity_results[fn.offset] = (similarity, result_function.name)

        output_file = pathlib.Path(sig_name)
        output_file.write_text(json.dumps(similarity_results))
        print("""Use the following script in IDA to rename functions with your signatures:
import pathlib
import json
from ida_name import set_name 

signature_path = ...
content = pathlib.Path(signature_path).read_text()
d = json.loads(content)

for k, v in d.items():
    prob, name = v[0], v[1]
    set_name(int(k), name, 1)""")
        return output_file

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

    @cache.cache(expire=72000)
    def _get_lib_functions_hashes(self, lib: pathlib.Path) -> list[PythonProviderFunction]:
        d = Disassembler()
        pdb_path = None
        if lib.with_suffix(".pdb").exists():
            pdb_path = lib.with_suffix(".exe")
        report = d.disassembleFile(lib, pdb_path=pdb_path)
        result: list[PythonProviderFunction] = []
        for fn in report.getFunctions():
            code = self._hash_fn(fn)
            if len(code) > 20:
                result.append(
                    PythonProviderFunction(
                        name=fn.function_name if len(fn.function_name) > 0 else None, code=code, offset=fn.offset
                    )
                )

        return result
