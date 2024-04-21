import json
import logging
import os
import pathlib
import sys
import tempfile
from enum import Enum, auto

import ida_name
import idc
from idaapi import *


class ConfigMode(Enum):
    FUNCTION_MODE_MIN = auto()
    NON_AUTO_FUNCTIONS = FUNCTION_MODE_MIN
    LIBRARY_FUNCTIONS = auto()
    PUBLIC_FUNCTIONS = auto()
    ENTRY_POINT_FUNCTIONS = auto()
    ALL_FUNCTIONS = auto()
    USER_SELECT_FUNCTION = auto()
    FUNCTION_MODE_MAX = USER_SELECT_FUNCTION


def get_ida_logging_handler():
    """
    IDA logger should always be the first one (since it inits the env)
    """
    return logging.getLogger().handlers[0]


logging.basicConfig(level=logging.DEBUG)
get_ida_logging_handler().setLevel(logging.INFO)
g_logger = logging.getLogger("idb2pat")


class Config(object):
    def __init__(
        self,
        min_func_length=10,
        pointer_size=4,
        mode=ConfigMode.ALL_FUNCTIONS,
        pat_append=False,
        logfile="",
        loglevel="DEBUG",
        logenabled=False,
    ):
        super(Config, self).__init__()
        self.min_func_length = min_func_length
        # TODO: get pointer_size from IDA
        self.pointer_size = pointer_size
        if idc.__EA64__:
            self.pointer_size = 8
        self.mode = mode
        self.pat_append = pat_append
        self.logfile = logfile
        self.loglevel = getattr(logging, loglevel)
        self.logenabled = logenabled

    def update(self, vals):
        """
        Set these fields given a dict with a similar schema as this,
         possibly loaded from a JSON string.
        type vals: dict(string, object)
        """
        self.min_func_length = vals.get("min_func_length", self.min_func_length)
        self.pointer_size = vals.get("pointer_size", self.pointer_size)
        # TODO: make this a string, not magic number
        self.mode = vals.get("mode", self.mode)
        self.pat_append = vals.get("pat_append", self.pat_append)
        self.logfile = vals.get("logfile", self.logfile)
        self.logenabled = vals.get("logenabled", self.logenabled)

        if "loglevel" in vals:
            if hasattr(logging, vals["loglevel"]):
                self.loglevel = getattr(logging, vals["loglevel"])


# generated from IDB2SIG plugin updated by TQN
CRC16_TABLE = [
    0x0,
    0x1189,
    0x2312,
    0x329B,
    0x4624,
    0x57AD,
    0x6536,
    0x74BF,
    0x8C48,
    0x9DC1,
    0xAF5A,
    0xBED3,
    0xCA6C,
    0xDBE5,
    0xE97E,
    0xF8F7,
    0x1081,
    0x108,
    0x3393,
    0x221A,
    0x56A5,
    0x472C,
    0x75B7,
    0x643E,
    0x9CC9,
    0x8D40,
    0xBFDB,
    0xAE52,
    0xDAED,
    0xCB64,
    0xF9FF,
    0xE876,
    0x2102,
    0x308B,
    0x210,
    0x1399,
    0x6726,
    0x76AF,
    0x4434,
    0x55BD,
    0xAD4A,
    0xBCC3,
    0x8E58,
    0x9FD1,
    0xEB6E,
    0xFAE7,
    0xC87C,
    0xD9F5,
    0x3183,
    0x200A,
    0x1291,
    0x318,
    0x77A7,
    0x662E,
    0x54B5,
    0x453C,
    0xBDCB,
    0xAC42,
    0x9ED9,
    0x8F50,
    0xFBEF,
    0xEA66,
    0xD8FD,
    0xC974,
    0x4204,
    0x538D,
    0x6116,
    0x709F,
    0x420,
    0x15A9,
    0x2732,
    0x36BB,
    0xCE4C,
    0xDFC5,
    0xED5E,
    0xFCD7,
    0x8868,
    0x99E1,
    0xAB7A,
    0xBAF3,
    0x5285,
    0x430C,
    0x7197,
    0x601E,
    0x14A1,
    0x528,
    0x37B3,
    0x263A,
    0xDECD,
    0xCF44,
    0xFDDF,
    0xEC56,
    0x98E9,
    0x8960,
    0xBBFB,
    0xAA72,
    0x6306,
    0x728F,
    0x4014,
    0x519D,
    0x2522,
    0x34AB,
    0x630,
    0x17B9,
    0xEF4E,
    0xFEC7,
    0xCC5C,
    0xDDD5,
    0xA96A,
    0xB8E3,
    0x8A78,
    0x9BF1,
    0x7387,
    0x620E,
    0x5095,
    0x411C,
    0x35A3,
    0x242A,
    0x16B1,
    0x738,
    0xFFCF,
    0xEE46,
    0xDCDD,
    0xCD54,
    0xB9EB,
    0xA862,
    0x9AF9,
    0x8B70,
    0x8408,
    0x9581,
    0xA71A,
    0xB693,
    0xC22C,
    0xD3A5,
    0xE13E,
    0xF0B7,
    0x840,
    0x19C9,
    0x2B52,
    0x3ADB,
    0x4E64,
    0x5FED,
    0x6D76,
    0x7CFF,
    0x9489,
    0x8500,
    0xB79B,
    0xA612,
    0xD2AD,
    0xC324,
    0xF1BF,
    0xE036,
    0x18C1,
    0x948,
    0x3BD3,
    0x2A5A,
    0x5EE5,
    0x4F6C,
    0x7DF7,
    0x6C7E,
    0xA50A,
    0xB483,
    0x8618,
    0x9791,
    0xE32E,
    0xF2A7,
    0xC03C,
    0xD1B5,
    0x2942,
    0x38CB,
    0xA50,
    0x1BD9,
    0x6F66,
    0x7EEF,
    0x4C74,
    0x5DFD,
    0xB58B,
    0xA402,
    0x9699,
    0x8710,
    0xF3AF,
    0xE226,
    0xD0BD,
    0xC134,
    0x39C3,
    0x284A,
    0x1AD1,
    0xB58,
    0x7FE7,
    0x6E6E,
    0x5CF5,
    0x4D7C,
    0xC60C,
    0xD785,
    0xE51E,
    0xF497,
    0x8028,
    0x91A1,
    0xA33A,
    0xB2B3,
    0x4A44,
    0x5BCD,
    0x6956,
    0x78DF,
    0xC60,
    0x1DE9,
    0x2F72,
    0x3EFB,
    0xD68D,
    0xC704,
    0xF59F,
    0xE416,
    0x90A9,
    0x8120,
    0xB3BB,
    0xA232,
    0x5AC5,
    0x4B4C,
    0x79D7,
    0x685E,
    0x1CE1,
    0xD68,
    0x3FF3,
    0x2E7A,
    0xE70E,
    0xF687,
    0xC41C,
    0xD595,
    0xA12A,
    0xB0A3,
    0x8238,
    0x93B1,
    0x6B46,
    0x7ACF,
    0x4854,
    0x59DD,
    0x2D62,
    0x3CEB,
    0xE70,
    0x1FF9,
    0xF78F,
    0xE606,
    0xD49D,
    0xC514,
    0xB1AB,
    0xA022,
    0x92B9,
    0x8330,
    0x7BC7,
    0x6A4E,
    0x58D5,
    0x495C,
    0x3DE3,
    0x2C6A,
    0x1EF1,
    0xF78,
]


# ported from IDB2SIG plugin updated by TQN
def crc16(data, crc):
    for byte in data:
        crc = (crc >> 8) ^ CRC16_TABLE[(crc ^ ord(byte)) & 0xFF]
    crc = (~crc) & 0xFFFF
    crc = (crc << 8) | ((crc >> 8) & 0xFF)
    return crc & 0xFFFF


def get_functions():
    for i in range(get_func_qty()):
        yield getn_func(i)


# TODO: idaapi.get_func(ea)
_g_function_cache = None


def get_func_at_ea(ea):
    """
    type ea: idc.ea_t
    """
    global _g_function_cache
    if _g_function_cache is None:
        _g_function_cache = {}
        for f in get_functions():
            _g_function_cache[f.start_ea] = f

    return _g_function_cache.get(f.start_ea, None)


def to_bytestring(seq):
    """
    convert sequence of chr()-able items to a str of
     their chr() values.
    in reality, this converts a list of uint8s to a
     bytestring.
    """
    return "".join(map(chr, seq))


class FuncTooShortException(Exception):
    pass


# ported from IDB2SIG plugin updated by TQN
def make_func_sig(config, func):
    """
    type config: Config
    type func: idc.func_t
    """
    logger = logging.getLogger("idb2pat:make_func_sig")

    if func.end_ea - func.start_ea < config.min_func_length:
        logger.debug("Function is too short")
        raise FuncTooShortException()

    ea = func.start_ea
    publics = []  # type: idc.ea_t
    refs = {}  # type: dict(idc.ea_t, idc.ea_t)
    variable_bytes = set([])  # type: set of idc.ea_t
    found_x86thunk_call = False
    call_next_pop = False

    while ea != BADADDR and ea < func.end_ea:
        logger.debug("ea: %s", hex(ea))

        instruction = ida_ua.insn_t()
        ida_ua.decode_insn(instruction, ea)

        name = get_name(ea)
        if name is not None and name != "":
            logger.debug("has a name")
            publics.append(ea)

        if instruction.get_canon_mnem() == "call" and ida_name.get_ea_name(
            instruction.ops[0].addr
        ).startswith("__x86.get_pc_thunk"):
            found_x86thunk_call = True

        elif instruction.get_canon_mnem() == "add" and found_x86thunk_call:
            found_x86thunk_call = False
            address_operand_start = ea + instruction.ops[1].offb
            address_operand_end = address_operand_start + idc.get_item_size(
                address_operand_start
            )

            for i in range(address_operand_start, address_operand_end):
                variable_bytes.add(i)

        if call_next_pop:
            found_x86thunk_call = True
            call_next_pop = False

        if (
            instruction.get_canon_mnem() == "call"
            and get_bytes(ea, instruction.size) == b"\xe8\x00\x00\x00\x00"
        ):
            call_next_pop = True

        for operand in instruction.ops:
            if operand.type == idc.o_void:
                break

            elif (
                # If the operand is data reference, and it references the CS segment register,
                # consider the operand to be variant bytes.
                # The referenced segment register is encoded in the high bytes of op_t.specval.
                (
                    operand.type == idc.o_mem
                    and operand.specval >> 16 == ida_segregs.R_cs
                )
                # If the operand is a code reference outside of the function,
                # consider the operand to be variant bytes.
                or (
                    operand.type in (idc.o_far, idc.o_near)
                    and operand.addr not in range(func.start_ea, func.end_ea)
                )
            ):
                address_operand_start = ea + operand.offb
                address_operand_end = address_operand_start + idc.get_item_size(
                    address_operand_start
                )
                print(f'Variable {address_operand_start:x}-{address_operand_end:x}')
                for i in range(address_operand_start, address_operand_end):
                    variable_bytes.add(i)

                refs[address_operand_start] = operand.addr

        ea = next_not_tail(ea)

    sig = ""
    # first 32 bytes, or til end of function
    for ea in range(func.start_ea, min(func.start_ea + 32, func.end_ea)):
        if ea in variable_bytes:
            sig += ".."
        else:
            sig += "%02X" % (get_byte(ea))

    sig += ".." * int(32 - (len(sig) / 2))

    if func.end_ea - func.start_ea > 32:
        crc_data = [0 for i in range(256)]

        # for 255 bytes starting at index 32, or til end of function, or variable byte
        for loc in range(32, min(func.end_ea - func.start_ea, 32 + 255)):
            if func.start_ea + loc in variable_bytes:
                break

            crc_data[loc - 32] = get_byte(func.start_ea + loc)
        else:
            loc += 1

        # TODO: is this required everywhere? ie. with variable bytes?
        alen = loc - 32

        crc = crc16(to_bytestring(crc_data[:alen]), crc=0xFFFF)
    else:
        loc = func.end_ea - func.start_ea
        alen = 0
        crc = 0

    sig += " %02X" % (alen)
    sig += " %04X" % (crc)
    # TODO: does this need to change for 64bit?
    sig += " %04X" % (func.end_ea - func.start_ea)

    # this will be either " :%04d %s" or " :%08d %s"
    public_format = " :%%0%dX %%s" % (config.pointer_size)
    for public in publics:
        name = get_name(public)
        if name is None or name == "":
            continue

        sig += public_format % (public - func.start_ea, name)

    for ref_loc, ref in refs.items():
        name = get_name(ref)
        if name is None or name == "":
            continue

        if ref_loc >= func.start_ea:
            # this will be either " ^%04d %s" or " ^%08d %s"
            addr = ref_loc - func.start_ea
            ref_format = " ^%%0%dX %%s" % (config.pointer_size)
        else:
            # this will be either " ^-%04d %s" or " ^-%08d %s"
            addrs = func.start_ea - ref_loc
            ref_format = " ^-%%0%dX %%s" % (config.pointer_size)
        sig += ref_format % (addr, name)

    # Tail of the module starts at the end of the CRC16 block.
    if loc < func.end_ea - func.start_ea:
        tail = " "
        for ea in range(func.start_ea + loc, min(func.end_ea, func.start_ea + 0x8000)):
            if ea in variable_bytes:
                tail += ".."
            else:
                tail += "%02X" % (get_byte(ea))
        sig += tail

    logger.debug("sig: %s", sig)
    print(sig)
    return sig


def make_func_sigs(config):
    logger = logging.getLogger("idb2pat:make_func_sigs")
    sigs = []
    if config.mode == ConfigMode.USER_SELECT_FUNCTION:
        f = choose_func("Choose Function:", BADADDR)
        if f is None:
            logger.error("No function selected")
            return []
        jumpto(f.start_ea)
        if not has_any_name(get_full_flags(f.start_ea)):
            logger.error("Function doesn't have a name")
            return []

        try:
            sigs.append(make_func_sig(config, f))
        except Exception as e:
            logger.exception(e)
            # TODO: GetFunctionName?
            logger.error(
                "Failed to create signature for function at %s (%s)",
                hex(f.start_ea),
                get_name(f.start_ea) or "",
            )

    elif config.mode == ConfigMode.NON_AUTO_FUNCTIONS:
        for f in get_functions():
            if has_name(get_full_flags(f.start_ea)) and f.flags & FUNC_LIB == 0:
                try:
                    sigs.append(make_func_sig(config, f))
                except FuncTooShortException:
                    pass
                except Exception as e:
                    logger.exception(e)
                    logger.error(
                        "Failed to create signature for function at %s (%s)",
                        hex(f.start_ea),
                        get_name(f.start_ea) or "",
                    )

    elif config.mode == ConfigMode.LIBRARY_FUNCTIONS:
        for f in get_functions():
            if has_name(get_full_flags(f.start_ea)) and f.flags & FUNC_LIB != 0:
                try:
                    sigs.append(make_func_sig(config, f))
                except FuncTooShortException:
                    pass
                except Exception as e:
                    logger.exception(e)
                    logger.error(
                        "Failed to create signature for function at %s (%s)",
                        hex(f.start_ea),
                        get_name(f.start_ea) or "",
                    )

    elif config.mode == ConfigMode.PUBLIC_FUNCTIONS:
        for f in get_functions():
            if is_public_name(f.start_ea):
                try:
                    sigs.append(make_func_sig(config, f))
                except FuncTooShortException:
                    pass
                except Exception as e:
                    logger.exception(e)
                    logger.error(
                        "Failed to create signature for function at %s (%s)",
                        hex(f.start_ea),
                        get_name(f.start_ea) or "",
                    )

    elif config.mode == ConfigMode.ENTRY_POINT_FUNCTIONS:
        for i in range(get_func_qty()):
            f = get_func(get_entry(get_entry_ordinal(i)))
            if f is not None:
                try:
                    sigs.append(make_func_sig(config, f))
                except FuncTooShortException:
                    pass
                except Exception as e:
                    logger.exception(e)
                    logger.error(
                        "Failed to create signature for function at %s (%s)",
                        hex(f.start_ea),
                        get_name(f.start_ea) or "",
                    )

    elif config.mode == ConfigMode.ALL_FUNCTIONS:
        n = get_func_qty()
        for i, f in enumerate(get_functions()):
            try:
                logger.info(
                    "[ %d / %d ] %s %s", i + 1, n, get_name(f.start_ea), hex(f.start_ea)
                )
                sigs.append(make_func_sig(config, f))
            except FuncTooShortException:
                pass
            except Exception as e:
                logger.exception(e)
                logger.error(
                    "Failed to create signature for function at %s (%s)",
                    hex(f.start_ea),
                    get_name(f.start_ea) or "",
                )

    return sigs


def get_pat_file():
    logger = logging.getLogger("idb2pat:get_pat_file")
    name, extension = os.path.splitext(get_input_file_path())
    name = name + ".pat"

    filename = ask_file(1, name, "Enter the name of the pattern file")
    if filename is None:
        logger.debug("User did not choose a pattern file")
        return None

    return filename


def update_config(config):
    logger = logging.getLogger("idb2pat:update_config")
    name, extension = os.path.splitext(get_input_file_path())
    name = name + ".conf"

    if not os.path.exists(name):
        logger.debug("No configuration file provided, using defaults")
        return

    with open(name, "rb") as f:
        t = f.read()

    try:
        vals = json.loads(t)
    except Exception as e:
        logger.exception(e)
        logger.warning("Configuration file invalid")
        return

    config.update(vals)
    return


def main():
    if os.name == "nt":
        try:
            load_and_run_plugin("pdb", 3)  # Creates proper netnodes we need
        except:
            pass
        n = netnode("$ pdb")
        n.altset(0, get_imagebase())
        n.supset(0, get_input_file_path()[:-4] + ".pdb")
        try:
            load_and_run_plugin("pdb", 3)

        except:  # If non windows, might not have a .pdb file
            pass

    c = Config(min_func_length=5)
    update_config(c)
    # if c.logenabled:
    # h = logging.FileHandler('/tmp/idb2pat.log')
    # h.setLevel(c.loglevel)
    # logging.getLogger().addHandler(h)
    # g_logger.info(idc.ARGV[0])
    # g_logger.info(idc.ARGV[1])
    filename = idc.ARGV[1]

    if filename is None:
        g_logger.debug("No file selected")
        ida_pro.qexit(0)

    sigs = make_func_sigs(c)

    f_flags = "ab" if c.pat_append else "wb"
    with open(filename, f_flags) as f:
        for sig in sigs:
            f.write(sig.encode("ascii"))
            f.write(b"\r\n")
        f.write(b"---")
        f.write(b"\r\n")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
