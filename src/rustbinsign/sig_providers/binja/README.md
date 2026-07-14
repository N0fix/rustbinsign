# WARP Integration w/ `rustbinsign`
Note that this too requires a paid license (i.e. I (nubbsterr) cannot test this myself. Hopefully stuff works though.)
- [Check out this documentation for info on applicable licenses and API installation.](https://docs.binary.ninja/dev/batch.html#install-the-api)
    - I am still confused on if this provider requires the GUI to be running or not, as this would change the required licenses to use this provider.

# Documentation/Sources
- [Binary Ninja's warp_ninja Rust crate source (not needed, but good for reference, since this is the underlying logic for the Python API)](https://github.com/Vector35/binaryninja-api/tree/dev/plugins/warp)
    - [User documentation](https://github.com/Vector35/binaryninja-api/blob/dev/docs/guide/warp.md)
    - [Warp Python API](https://github.com/Vector35/binaryninja-api/blob/dev/plugins/warp/api/python/warp.py)
        - [Examples](https://github.com/Vector35/binaryninja-api/blob/dev/docs/guide/warp.md#python-example)
    - [FFI source](https://github.com/Vector35/binaryninja-api/tree/dev/plugins/warp/src/plugin/ffi)
