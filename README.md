Search for dependencies inside a compiled rust executable, download them and create a signature.

- Give information about the version of the compiler used
- Give information about detected dependencies used
- Allows you to create a signature out of dependencies and proper rust std, using the right toolchain.
- Allows you to easily download a crate


| Before         | After         |
| -------------- | ------------- |
| ![Before](https://raw.githubusercontent.com/N0fix/imgs/d859ce0cdb6f5ead0b19c6b202a2fa5599365e2f/Screenshot%202023-12-22%20002750.png) | ![After](https://raw.githubusercontent.com/N0fix/imgs/d859ce0cdb6f5ead0b19c6b202a2fa5599365e2f/Screenshot%202023-12-22%20003431.png) |


# Install

```bash
git clone https://github.com/N0fix/rustbininfo
cd rustbininfo
poetry install
rustbininfo --help
```

# Help

```bash
usage: rustbininfo [-h] {info,download,sign,get_std_lib} ...

Rust script

options:
  -h, --help            show this help message and exit

mode:
  {info,download,sign,get_std_lib}
                        Mode to use
    info                Get information about an executable
    download            Download a crate. Exemple: rand_chacha-0.3.1
    sign                Generate a signature for a given executable, using choosed sig provider
    get_std_lib         Download stdlib with symbols for a specific version of rustc
```

# Example usage

## Info

```
> rustbininfo info C:\Users\user\Documents\flareon2023\infector.exe.mal_ 
[----    rustc     ----]
version: ~1.68.2 (9eb3afe9ebe9c7d2b84b71002d44f4a0edac95e0)

[---- Dependencies ----]
rand-0.8.5
rand_chacha-0.3.1
```

This can be used to apply the proper signature, available [here](https://github.com/N0fix/rust-std-sigs).

## Sign
```bash
> rustbininfo sign C:\Users\user\Downloads\crackme.exe crackme_signature IDA 'C:\Program Files\IDA Pro 8.3\idat64' "C:\Users\user\Downloads\sigmake.exe"
[...Should create a crackme.sig file that you can import into IDA]
```

# Extending the tool for other disassemblers

This tool is meant to be used with IDA. If you want to extend it to Ghidra, binja, r2, or watever tool you are using, just create a new provider that inherits `BaseSigProvider`. You might need to adapt the command line to add your provider's argument.

# FAQ

## How is it different from [Ariane](https://github.com/N0fix/Ariane) or [Cerberus](https://github.com/h311d1n3r/Cerberus/tree/main)?

While [Ariane](https://github.com/N0fix/Ariane) or [Cerberus](https://github.com/h311d1n3r/Cerberus/tree/main) tries to recognize functions and sign them themselves, reinventing the wheel, this tool focuses on providing accurate information about the Rust compiler (rustc) version used in your target, as well as its dependencies. I delegate function recognition and signature tasks to tools specifically designed for those purposes (IDA, binja...). These tasks are incredibly complex to execute correctly, and these tools perform them much more effectively than I could.

## How can I adapt it to Ghidra/Binary Ninja/X ?

This tool generates a signature using a signature provider defined under sig_providers/. You should be able to effortlessly add your own provider to generate a signature that your favorite tool will recognize.

## Limitations

First, Detected version of the compiler might not be exact. A better approach would be to pull the proper commit, build rust using `x.py` and add this to available toolchains.

Also, Rust allows for numerous optimizations, with inlining being one of them. inlined functions pose a challenge for signature generation and may go unrecognized by FLIRT, thereby undermining the primary objective of this tool.

Additionally, it's important to note that this tool compiles dependencies in release mode by default. However, there's a possibility that your target may not have compiled these dependencies in release mode.

Finally, this tool does its best as compiling as much features as your target dependencies expose, but might be missing some.

# Thanks

This tool uses the great Mandiant's [idb2pat](https://github.com/mandiant/flare-ida/blob/master/python/flare/idb2pat.py).