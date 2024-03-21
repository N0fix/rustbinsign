Search for dependencies inside a compiled rust executable, download them and create a signature.

- Allows you to create a signature out of dependencies and proper rust stdlib, using the right toolchain.
- Give information about the version of the compiler used
- Give information about detected dependencies used
- Allows you to easily download a crate


| Before         | After         |
| -------------- | ------------- |
| ![Before](https://raw.githubusercontent.com/N0fix/imgs/d859ce0cdb6f5ead0b19c6b202a2fa5599365e2f/Screenshot%202023-12-22%20002750.png) | ![After](https://raw.githubusercontent.com/N0fix/imgs/d859ce0cdb6f5ead0b19c6b202a2fa5599365e2f/Screenshot%202023-12-22%20003431.png) |


# Install

```bash
git clone https://github.com/N0fix/rustbinsign
cd rustbinsign
poetry install
rustbinsign --help
```

# Help

```bash
usage: rbi [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] {info,download,download_sign,sign_stdlib,sign_target,sign_libs,get_std_lib} ...

This script aims at facilitate creation of signatures for rust executables. It can detect dependencies and rustc version used in a target, and create signatures using a signature provider.

options:
  -h, --help            show this help message and exit
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level

mode:
  {info,download,download_sign,sign_stdlib,sign_target,sign_libs,get_std_lib}
                        Mode to use
    info                Get information about an executable
    download            Download a crate. Exemple: rand_chacha-0.3.1
    download_sign       Download a crate. And signs it. Exemple: rand_chacha-0.3.1
    sign_stdlib         Sign standard lib toolchain
    sign_target         Generate a signature for a given executable, using choosed signature provider
    sign_libs           Generate a signature for a given list of libs, using choosed signature provider
    get_std_lib         Download stdlib with symbols for a specific version of rustc

Usage examples:

 rustbinsign -l DEBUG info 'challenge.exe'
 rustbinsign download_sign IDA 'C:\Program Files\IDA Pro\idat64.exe' .\sigmake.exe hyper-0.14.27 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign download hyper-0.14.27
 rustbinsign sign_stdlib --template ./profiles/ivanti_rust_sample.json -t 1.70.0-x86_64-unknown-linux-musl IDA ~/idat64 ~/sigmake
 rustbinsign get_std_lib 1.70.0-x86_64-unknown-linux-musl
 rustbinsign sign_libs -l .\sha2-0.10.8\target\release\sha2.lib -l .\crypt-0.4.2\target\release\crypt.lib IDA 'C:\Program Files\IDA Pro\idat64.exe' .\sigmake.exe
 rustbinsign sign_target -t 1.70.0-x86_64-unknown-linux-musl  --target ~/Downloads/target --no-std --signature_name malware_1.70.0_musl
```

# Example usage

## Info

```
> rustbinsign info C:\Users\user\Documents\flareon2023\infector.exe.mal_ 
[----    rustc     ----]
version: ~1.68.2 (9eb3afe9ebe9c7d2b84b71002d44f4a0edac95e0)

[---- Dependencies ----]
rand-0.8.5
rand_chacha-0.3.1
```

This can be used to apply the proper signature, available [here](https://github.com/N0fix/rust-std-sigs).

# Requirements

You have to build on the same platform then the platform used to build your target (likely linux if your target is an ELF, likely windows if your target is an EXE).
IDA's provider requires IDA with IDAPython.

# Extending the tool for other disassemblers

This tool is meant to be used with IDA. If you want to extend it to Ghidra, binja, r2, or watever tool you are using, just create a new provider that inherits `BaseSigProvider`. You might need to adapt the command line to add your provider's argument.

# FAQ

## How is it different from [Ariane](https://github.com/N0fix/Ariane) or [Cerberus](https://github.com/h311d1n3r/Cerberus/tree/main)?

While [Ariane](https://github.com/N0fix/Ariane) or [Cerberus](https://github.com/h311d1n3r/Cerberus/tree/main) tries to recognize functions and sign them themselves, reinventing the wheel, this tool focuses on providing accurate information about the Rust compiler (rustc) version used in your target, as well as its dependencies. I delegate function recognition and signature tasks to tools specifically designed for those purposes (IDA, binja...). These tasks are incredibly complex to execute correctly, and these tools perform them much more effectively than I could.

## How can I adapt it to Ghidra/Binary Ninja/X ?

This tool generates a signature using a signature provider defined under sig_providers/. You should be able to effortlessly add your own provider to generate a signature that your favorite tool will recognize.

## Limitations

Limitations are described in [this blogpost](https://nofix.re/posts/2024-11-02-rust-symbs/).

# Thanks

This tool uses the great Mandiant's [idb2pat](https://github.com/mandiant/flare-ida/blob/master/python/flare/idb2pat.py).
