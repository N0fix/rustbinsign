import pathlib

from datasketch.minhash import MinHash
from smda.common import SmdaFunction
from smda.Disassembler import Disassembler

from ..provider_base import BaseSigProvider
from .model import ConfigPython


class PythonProvider(BaseSigProvider):
    cfg: ConfigPython

    def __init__(self, cfg: ConfigPython):
        if cfg is None:
            self.cfg = ConfigPython()

        else:
            self.cfg = cfg

    def generate_signature(self, libs: list[pathlib.Path], sig_name: str | None) -> pathlib.Path:
        results = []
        for lib in libs:
            print(f"Signing {lib}")
            r = self._get_lib_functions_hashes(lib)
            results.append({"name": lib.name, "functions": r})
            # output_file = pathlib.Path(".") / lib.name
            # output_file.write_text(json.dumps(json.load()), indent=4)

        if self.cfg.target:
            target = self._get_lib_functions_hashes(self.cfg.target)
            for fn in target:
                if fn["offset"] == 0x814D4:
                    m2 = MinHash()
                    second_fn = [fn["code"][i : i + 2] for i in range(0, len(fn["code"]), 2)]
                    for data in second_fn:
                        m2.update(data.encode())
                    for _ in results:
                        for _ff in _["functions"]:
                            m1 = MinHash()
                            first_fn = [_ff["code"][i : i + 2] for i in range(0, len(_ff["code"]), 2)]
                            for data in first_fn:
                                m1.update(data.encode())
                            print(m1.jaccard(m2), _["name"], _ff["name"])

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

    def _get_lib_functions_hashes(self, lib: pathlib.Path) -> list:
        d = Disassembler()
        report = d.disassembleFile(lib)
        result = []
        for fn in report.getFunctions():
            code = self._hash_fn(fn)
            if len(code) > 20:
                result.append({"name": fn.function_name, "code": code, "offset": fn.offset})

        return result
