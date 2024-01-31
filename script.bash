#/bin/bash
ARCH=$1
TARGET=$ARCH-linux-musl

# Don't depend on the mirrors of sabotage linux that musl-cross-make uses.
LINUX_HEADERS_SITE=https://ci-mirrors.rust-lang.org/rustc/sabotage-linux-tarballs
LINUX_VER=headers-4.19.88

OUTPUT=/usr/local
shift

# Ancient binutils versions don't understand debug symbols produced by more recent tools.
# Apparently applying `-fPIC` everywhere allows them to link successfully.
# Enable debug info. If we don't do so, users can't debug into musl code,
# debuggers can't walk the stack, etc. Fixes #90103.
export CFLAGS="-fPIC -g1 $CFLAGS"

git clone https://github.com/richfelker/musl-cross-make # -b v0.9.9
cd musl-cross-make
# A version that includes support for building musl 1.2.3
#git checkout fe915821b652a7fa37b34a596f47d8e20bc72338

git checkout a54eb56f33f255dfca60be045f12a5cfaf5a72a9

MVER=1.1.24

#hide_output
make -j$(nproc) TARGET=$TARGET MUSL_VER=$MVER LINUX_HEADERS_SITE=$LINUX_HEADERS_SITE LINUX_VER=$LINUX_VER
#hide_output 
make install TARGET=$TARGET MUSL_VER=$MVER LINUX_HEADERS_SITE=$LINUX_HEADERS_SITE LINUX_VER=$LINUX_VER OUTPUT=/tmp/musl/output
#$OUTPUT
