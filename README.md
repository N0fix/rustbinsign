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
usage: rbs [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] {info,download,compile,compile_target,download_sign,download_compile,sign_stdlib,sign_target,sign_libs,get_std_lib,guess_project_creation_timestamp} ...

This script aims at facilitate creation of signatures for rust executables. It can detect dependencies and rustc version used in a target, and create signatures using a signature provider.

options:
  -h, --help            show this help message and exit
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level

mode:
  {info,download,compile,compile_target,download_sign,download_compile,sign_stdlib,sign_target,sign_libs,get_std_lib,guess_project_creation_timestamp}
                        Mode to use
    info                Get information about an executable
    download            Download a crate. Exemple: rand_chacha-0.3.1
    compile             Compiles a crate. Exemple: rand_chacha-0.3.1
    compile_target      Compiles all dependencies detected in target compiled rust executable.
    download_sign       Download a crate and signs it. Exemple: rand_chacha-0.3.1
    download_compile    Download a crate and compiles it. Exemple: rand_chacha-0.3.1
    sign_stdlib         Sign standard lib toolchain
    sign_target         Generate a signature for a given executable, using choosed signature provider
    sign_libs           Generate a signature for a given list of libs, using choosed signature provider
    get_std_lib         Download stdlib with symbols for a specific version of rustc
    guess_project_creation_timestamp
                        Tries to guess the compilation date based on dependencies version

Usage examples:
 rustbinsign sign_target -t 1.70.0-x86_64-unknown-linux-musl --provider IDA --target sample.bin --no-std --signature_name malware_1.70.0_musl

 rustbinsign -l DEBUG info 'challenge.exe'
 rustbinsign download_sign --provider IDA hyper-0.14.27 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign download hyper-0.14.27
 rustbinsign compile --template ./profile/ctf.json /tmp/rustbininfo/rand_chacha-0.3.1/Cargo.toml 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign download_compile rand_chacha-0.3.1 1.70.0-x86_64-unknown-linux-gnu
 rustbinsign sign_stdlib --template ./profiles/ivanti_rust_sample.json -t 1.70.0-x86_64-unknown-linux-musl --provider IDA
 rustbinsign get_std_lib 1.70.0-x86_64-unknown-linux-musl
 rustbinsign sign_libs -l .\sha2-0.10.8\target\release\sha2.lib -l .\crypt-0.4.2\target\release\crypt.lib --provider IDA
```

# Example usage

## Info

```bash
$ rbs info sample.bin
TargetRustInfo(
    rustc_version='1.70.0',
    rustc_commit_hash='90c541806f23a127002de5b4038be731ba1458ca',
    dependencies=[
        Crate(name='addr2line', version='0.17.0', features=[], repository=None),
        Crate(name='aes', version='0.7.5', features=[], repository=None),
        Crate(name='bytes', version='1.4.0', features=[], repository=None),
        Crate(name='cfb-mode', version='0.7.1', features=[], repository=None),
        Crate(name='crossbeam-channel', version='0.5.8', features=[], repository=None),
        Crate(name='crossbeam-deque', version='0.8.3', features=[], repository=None),
        Crate(name='crossbeam-epoch', version='0.9.15', features=[], repository=None),
        Crate(name='futures-channel', version='0.3.28', features=[], repository=None),
        Crate(name='futures-core', version='0.3.28', features=[], repository=None),
        Crate(name='futures-util', version='0.3.28', features=[], repository=None),
        Crate(name='generic-array', version='0.14.7', features=[], repository=None),
        Crate(name='gimli', version='0.26.2', features=[], repository=None),
        Crate(name='hashbrown', version='0.12.3', features=[], repository=None),
        Crate(name='hex', version='0.4.3', features=[], repository=None),
        Crate(name='http', version='0.2.9', features=[], repository=None),
        Crate(name='httparse', version='1.8.0', features=[], repository=None),
        Crate(name='hyper', version='0.14.27', features=[], repository=None),
        Crate(name='mio', version='0.8.8', features=[], repository=None),
        Crate(name='once_cell', version='1.18.0', features=[], repository=None),
        Crate(name='rayon', version='1.7.0', features=[], repository=None),
        Crate(name='rayon-core', version='1.11.0', features=[], repository=None),
        Crate(name='self-replace', version='1.3.5', features=[], repository=None),
        Crate(name='socket2', version='0.4.9', features=[], repository=None),
        Crate(name='sysinfo', version='0.29.2', features=[], repository=None),
        Crate(name='tokio', version='1.29.0', features=[], repository=None),
        Crate(name='want', version='0.3.1', features=[], repository=None)
    ],
    rust_dependencies_imphash='4b15dc8e43b773df8900e7b194ada169',
    guessed_toolchain='Mingw-w64 (Mingw6-GCC_8.3.0)'
)
```

This can be used to apply the proper signature.

Some signatures of rust win stdlib are available [here](https://github.com/N0fix/rust-std-sigs).

# Requirements

You have to build on the same platform then the platform used to build your target (likely linux if your target is an ELF, likely windows if your target is an EXE).
Choosing IDA as your signature provider requires IDA with IDAPython. IDA provider is the only provider supported at the moment.

# Extending the tool for other disassemblers

This tool is meant to be used with IDA. If you want to extend it to Ghidra, binja, r2, or watever tool you are using, just create a new provider that inherits `BaseSigProvider`. You might need to adapt the command line to add your provider's argument.

# TODO (hopefully ?)

- [ ] Make a Dockerfile for easy installation and usage
- [ ] Make Dockerfiles to easy usage when signing mingw targets
- [ ] Implement a provider that does not require IDA with IDAPython, using [smda](https://github.com/danielplohmann/smda) 

# FAQ

## How is it different from [Ariane](https://github.com/N0fix/Ariane) or [Cerberus](https://github.com/h311d1n3r/Cerberus/tree/main)?

While [Ariane](https://github.com/N0fix/Ariane) or [Cerberus](https://github.com/h311d1n3r/Cerberus/tree/main) tries to recognize functions and sign them themselves, reinventing the wheel, this tool focuses on providing accurate information about the Rust compiler (rustc) version used in your target, as well as its dependencies. I delegate function recognition and signature tasks to tools specifically designed for those purposes (IDA, binja...). These tasks are incredibly complex to execute correctly, and these tools perform them much more effectively than I could.

## How can I adapt it to Ghidra/Binary Ninja/X ?

This tool generates a signature using a signature provider defined under sig_providers/. You should be able to effortlessly add your own provider to generate a signature that your favorite tool will recognize.

## Limitations

Limitations are described in [this blogpost](https://nofix.re/posts/2024-11-02-rust-symbs/).


# Thanks

This tool uses the great Mandiant's [idb2pat](https://github.com/mandiant/flare-ida/blob/master/python/flare/idb2pat.py).
