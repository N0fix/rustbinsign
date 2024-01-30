import pathlib
import pickle
import time
import multiprocessing as mp
from typing import List, Optional
from ..provider_base import BaseSigProvider
from .model import ConfigBinja
from binaryninja import *
from .sigkit import *
from .sigkit.sigkit import sig_serialize_fb, signaturelibrary
from .sigkit.sigkit.trie_ops import trie_insert_funcs
from .sigkit.sigkit.signaturelibrary import FunctionInfo, FunctionNode


class BinjaProvider(BaseSigProvider):
    cfg: ConfigBinja

    def __init__(self, cfg: ConfigBinja):
        self.cfg = cfg

    def generate_signature(self, libs: List[pathlib.Path], sig_name: Optional[str]) -> pathlib.Path:
        pattern = self.generate_pattern(libs)
        sig_path = Path(sig_name if sig_name else "signature").with_suffix(".sig")
        write_pattern(sig_path.with_suffix(".pkl"), pattern)
        write_sig(sig_path, pattern) 
        return sig_path

    def generate_pattern(self, libs: List[Path]) -> Dict[FunctionNode, FunctionInfo]:
        if not self.cfg.multiprocess:
            func_info = {}
            for lib in libs:
                lib_pattern = self.process_binary(lib)
                func_info = func_info.update(lib_pattern)
            return func_info
                
        workers = mp.cpu_count() // 4   # its all wrong here, wait for the --workers
        analysis_thread_count = mp.cpu_count() * 3 // 4
        wg = mp.Value('i', 0)
        results = mp.Queue()
        func_info = {}
        with mp.Pool(workers, initializer=init_child, initargs=(wg, results, analysis_thread_count)) as pool:
            pool.map(self.process_binary, libs)
            while True:
                time.sleep(0.1)
                with wg.get_lock():
                    if wg.value == 0:
                        break
            while not results.empty():
                new_pattern = results.get()
                func_info.update(new_pattern)
        return func_info

    def process_binary(self, input_binary: pathlib.Path) -> Optional[Dict[FunctionNode, FunctionInfo]]:
        disable_default_log()
        print(f'{input_binary}: loading')
        if self.cfg.multiprocess:
            global cpu_count
            Settings().set_integer("analysis.limits.workerThreadCount", cpu_count)
        binary_name = input_binary.name
        if binary_name.endswith('.dll'):
            bv = binaryninja.BinaryViewType["PE"].open(input_binary)
            #cxt = PluginCommandContext(bv)
            #PluginCommand.get_valid_list(cxt)['PDB\\Load (BETA)'].execute(cxt)
        elif binary_name.endswith('.o') or binary_name.endswith('.so'):
            bv = binaryninja.BinaryViewType["ELF"].open(input_binary)
        else:
            raise ValueError('unsupported input file', input_binary)
        if not bv:
            print(f'Failed to load {input_binary}')
            return
        print(f'Analysing {input_binary}')
        if not self.cfg.multiprocess:
            bv.update_analysis_and_wait()
            return process_bv(bv)
        global wg
        with wg.get_lock():
            wg.value+=1
        AnalysisCompletionEvent(bv, on_analysis_complete)
        bv.update_analysis()

def process_bv(bv: BinaryView) -> Dict[FunctionNode, FunctionInfo]:
    lib_pattern = {}
    print(bv.file.filename, ': processing')
    guess_relocs = len(bv.relocation_ranges) == 0
    for func in bv.functions:
        try:
            if bv.get_symbol_at(func.start) is None: continue
            node, info = generate_function_signature(func, guess_relocs)
            lib_pattern[node] = info
            print("Processed", func.name)
        except:
            import traceback
            traceback.print_exc()
    return lib_pattern

def on_analysis_complete(bv: BinaryView):
    global wg, results
    lib_patterns = process_bv(bv)
    results.put(lib_patterns)
    with wg.get_lock():
        wg.value -= 1
    print(bv.file.filename, ": done")
    bv.file.close()
    if not lib_patterns:
        print(f"{bv.file.filename}: failed to generate pattern")
        return
    pattern_path = Path(f"{bv.file.filename}.pkl") # TODO cli --directory argument
    write_pattern(pattern_path, lib_patterns)

def init_child(wg_, results_, cpu_count_):
    global wg, results, cpu_count
    wg, results, cpu_count = wg_, results_, cpu_count_

def write_pattern(path: Path, lib_patterns: Dict[FunctionNode, FunctionInfo]):
    try:
        with open(path, "wb") as f:
            pickle.dump(lib_patterns, f)
    except Exception as e:
        print(f"oopsi, write_pattern failed: {e}")
        
def write_sig(signature_path: Path, pattern: Dict[FunctionNode, FunctionInfo]):
    trie = signaturelibrary.new_trie()
    trie_insert_funcs(trie, pattern)
    buf = sig_serialize_fb.SignatureLibraryWriter().serialize(trie)
    with open(signature_path, "wb") as f:
        f.write(buf)