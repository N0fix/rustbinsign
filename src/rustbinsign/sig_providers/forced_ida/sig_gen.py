import ida_pro
from ida_diskio import getsysfile
from ida_loader import load_and_run_plugin
from idaapi import netnode

n = netnode("$PLUGIN-MAKESIG")
n.supset(0, get_input_file_path() + ".sig")
n.supset(1, "libname")
n.supset(2, "")
n.supset(3, "")
load_and_run_plugin(getsysfile("makesig64_patched.so", "plugins"), 1)

ida_pro.qexit(0)
