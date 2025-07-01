import contextlib
import pathlib
import re
import struct
import sys

import lief
from construct import ExprValidator, Int64ul, Struct, ValidationError

plugin_vtable = Struct(
    "empty1" / ExprValidator(Int64ul, lambda obj_, _: obj_ == 0),
    "empty2" / ExprValidator(Int64ul, lambda obj_, _: obj_ == 0),
    "generate_sigs_fn" / ExprValidator(Int64ul, lambda obj_, _: 0x1000 <= obj_ < 0xFFFF),
    "fill_fn" / ExprValidator(Int64ul, lambda obj_, _: 0x1000 <= obj_ < 0xFFFF),
    "nullsub" / ExprValidator(Int64ul, lambda obj_, _: 0x1000 <= obj_ < 0xFFFF),
    "free_fn" / ExprValidator(Int64ul, lambda obj_, _: 0x1000 <= obj_ < 0xFFFF),
)


class LiefParsed:
    def get_export(name): ...

    def virtual_address_to_offset(self, va): ...

    def get_plugin_entry_call_pat(self): ...

    def get_plugin_entry_end_pat(self): ...

    def get_sig_gen_jmp_pat(self): ...

    def get_lib_ext(self): ...

    def get_call_patch(self, to_va: int, from_va: int, pos_va: int): ...


class LiefPE(LiefParsed):
    def __init__(self, target: pathlib.Path):
        self.pe = lief.PE.parse(target)

    def get_plugin_entry_call_pat(self):
        pat = rb"\xff\x10"  # call qword ptr [rax]
        return pat

    def get_plugin_entry_end_pat(self):
        end_of_fn = rb"\x48\x8B\xC3.{5}\x48\x83\xc4\x60.{1,3}\xc3"
        return end_of_fn

    def get_sig_gen_jmp_pat(self):
        pat = rb"\x83\xF8\x01\x0F.{3}\x00\x00"
        return pat, b"\x90" * len(pat)

    def get_lib_ext(self):
        return ".dll"

    def rva_to_offset(self, rva):
        return self.pe.rva_to_offset(rva)

    def va_to_offset(self, va):
        return self.pe.va_to_offset(va)

    def get_call_patch(self, to_va: int, from_va: int, pos_va: int):
        mov_rcx_rbx = bytes.fromhex("48 89 d9")
        call_target = b"\xe8" + struct.pack("<I", to_va - from_va - 5 - len(mov_rcx_rbx))
        jmp_loc = from_va + len(call_target) + len(mov_rcx_rbx)

        jmp = bytes.fromhex(f"EB {pos_va - jmp_loc - 2 - 19:02x}")
        return mov_rcx_rbx + call_target + jmp

    def get_export(self, name):
        for entry in self.pe.get_export().entries:
            if entry.name == name:
                return entry


class LiefELF(LiefParsed):
    def __init__(self, target: pathlib.Path):
        self.elf = lief.ELF.parse(target)

    def get_export(self, name):
        return self.elf.export_symbol(name)

    def virtual_address_to_offset(self, va):
        return self.elf.virtual_address_to_offset(va)

    def get_call_patch(self, to_va: int, from_va: int, pos_va: int):
        mov_rdi_rbx = bytes.fromhex("48 89 df")
        call_target = b"\xe8" + struct.pack("<I", to_va - from_va - 5 - len(mov_rdi_rbx))
        jmp_loc = from_va + len(call_target) + len(mov_rdi_rbx)

        jmp = bytes.fromhex(f"EB {pos_va - jmp_loc - 2 - 19:02x}")
        return mov_rdi_rbx + call_target + jmp

    def get_lib_ext(self):
        return ".so"

    def get_plugin_entry_call_pat(self):
        pat = rb"\xff\x55\x00"  # call qword ptr [rbp+0]
        return pat

    def get_plugin_entry_end_pat(self):
        end_of_fn = rb"\x48\x83\xc4.{3,6}\xc3"
        return end_of_fn

    def get_sig_gen_jmp_pat(self):
        pat = rb"\x0F.{3}\x00\x00\x48\x89\xDF\xE8"
        return pat, b"\x90" * 6


# TODO: fix arbitrary 0x1ACE0 and - 19
filename = sys.argv[1]
content = pathlib.Path(filename).read_bytes()


def get_sig_generation_fn_va() -> int:
    start = 0x1ACE0
    for i in range(start, start + 0x100, 8):
        with contextlib.suppress(ValidationError):
            vtbl = plugin_vtable.parse(content[i : i + 6 * 8])
            return vtbl.generate_sigs_fn

if filename.endswith(".dll"):
    target = LiefPE(pathlib.Path(filename))
    print("PE version doesn't work yet", file=sys.stderr)
    exit(1)


elif filename.endswith(".so"):
    target = LiefELF(pathlib.Path(filename))

else:
    print("Invalid input file", file=sys.stderr)
    exit(1)

s = target.get_export("PLUGIN")
plugin_pa = target.virtual_address_to_offset(s.value)
print(f"Plugin PA: {plugin_pa:x}")
plugin_ep_va = struct.unpack("<Q", content[plugin_pa + 8 : plugin_pa + 16])[0]
plugin_ep_pa = target.virtual_address_to_offset(plugin_ep_va)

pat = target.get_plugin_entry_call_pat()
end_of_fn = target.get_plugin_entry_end_pat()  # rb"\x48\x83\xc4.{3,6}\xc3"

print(f"Fn PA: {plugin_ep_pa:x}")
match = next(re.finditer(pat, content[plugin_ep_pa : plugin_ep_pa + 0x200]))
addr_to_patch = plugin_ep_pa + match.end()
match = next(re.finditer(end_of_fn, content[addr_to_patch : addr_to_patch + 0x200]))
end_of_fn_va = addr_to_patch + match.start()
print(f"End of plugin init: {end_of_fn_va:x}")

print(f"Sig generation fn: {get_sig_generation_fn_va():x}")
call_patch = target.get_call_patch(
    target.virtual_address_to_offset(get_sig_generation_fn_va()),
    target.virtual_address_to_offset(addr_to_patch),
    target.virtual_address_to_offset(end_of_fn_va),
)


content = content[:addr_to_patch] + call_patch + content[addr_to_patch + len(call_patch) :]

pat, repl = (
    target.get_sig_gen_jmp_pat()
)  # This skips the need of opening a menue, as long as we insert data into netnodes before calling the plugin
match = next(
    re.finditer(
        pat,
        content[
            target.virtual_address_to_offset(get_sig_generation_fn_va()) : target.virtual_address_to_offset(
                get_sig_generation_fn_va()
            )
            + 0x200
        ],
    )
)
addr_to_patch = target.virtual_address_to_offset(get_sig_generation_fn_va()) + match.start()
print(f"Form jump to patch: {addr_to_patch:x}")
content = content[:addr_to_patch] + repl + content[addr_to_patch + len(repl) :]


pathlib.Path(str(filename).strip(".so.bak") + "_patched" + target.get_lib_ext()).write_bytes(content)

print(f"Wrote to {str(filename).strip('.so.bak') + '_patched' + target.get_lib_ext()}")
