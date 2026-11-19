#!/bin/bash
# SPDX-License-Identifier: MIT
# Check the agreed ARM64 Linux VM toolchain without installing or booting it.
set -u
if [[ $# != 1 || ! -f $1/Makefile || ! -f $1/.config ]]; then
    echo "usage: $0 CONFIGURED_KERNEL_SOURCE" >&2
    exit 2
fi
camera_tree=$(realpath "$1")
camera_failures=0
camera_fail() { echo "FAIL: $*"; camera_failures=$((camera_failures + 1)); }
echo "Profile: aarch64 Arch Linux VM, Clang/LLVM 21.1.8, Rust 1.93.1"
echo "Host: $(uname -s) $(uname -m)"
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]] || camera_fail "run this profile inside the ARM64 Linux VM"
for camera_tool in git make clang ld.lld llvm-ar llvm-nm llvm-objcopy llvm-objdump llvm-strip \
    bc bison flex openssl pkg-config python3 patch tar xz cpio perl rsync depmod sha256sum nproc; do
    command -v "$camera_tool" >/dev/null || camera_fail "missing command: $camera_tool"
done
camera_rustc=${RUSTC:-rustc}
camera_hostrustc=${HOSTRUSTC:-$camera_rustc}
camera_rustdoc=${RUSTDOC:-rustdoc}
camera_bindgen=${BINDGEN:-bindgen}
for camera_tool in "$camera_rustc" "$camera_hostrustc" "$camera_rustdoc" "$camera_bindgen"; do
    command -v "$camera_tool" >/dev/null || camera_fail "missing Rust command: $camera_tool"
done
if command -v clang >/dev/null; then
    camera_version=$(clang --version)
    echo "$camera_version"
    [[ $camera_version == *"version 21.1.8"* ]] || camera_fail "select the existing Clang 21.1.8 in PATH"
fi
if command -v ld.lld >/dev/null; then
    camera_version=$(ld.lld --version)
    echo "$camera_version"
    [[ $camera_version == *"21.1.8"* ]] || camera_fail "LLD must match LLVM 21.1.8"
fi
for camera_tool in llvm-ar llvm-nm llvm-objcopy llvm-objdump llvm-strip; do
    if command -v "$camera_tool" >/dev/null; then
        camera_version=$("$camera_tool" --version)
        echo "$camera_tool: $camera_version"
        [[ $camera_version == *"21.1.8"* ]] || camera_fail "$camera_tool must match LLVM 21.1.8"
    fi
done
for camera_tool in "$camera_rustc" "$camera_hostrustc" "$camera_rustdoc"; do
    if command -v "$camera_tool" >/dev/null; then
        camera_version=$("$camera_tool" --version)
        echo "$camera_tool: $camera_version"
        [[ $camera_version == *"1.93.1"* ]] || camera_fail "$camera_tool must be the agreed Rust 1.93.1 tool"
    fi
done
if command -v "$camera_bindgen" >/dev/null; then
    "$camera_bindgen" --version
    echo "Reference bindgen version: 0.72.1; compatibility is checked by kbuild below."
fi
if command -v pkg-config >/dev/null; then
    pkg-config --exists openssl || camera_fail "OpenSSL development headers/pkg-config metadata missing"
    pkg-config --exists libelf || camera_fail "libelf development headers/pkg-config metadata missing"
fi
if command -v "$camera_rustc" >/dev/null; then
    camera_sysroot=$("$camera_rustc" --print sysroot)
    camera_rustsrc=${RUST_LIB_SRC:-$camera_sysroot/lib/rustlib/src/rust/library}
    echo "Rust sysroot: $camera_sysroot"
    echo "Rust library source: $camera_rustsrc"
    [[ -f $camera_rustsrc/core/src/lib.rs ]] || camera_fail "matching Rust 1.93.1 core sources are missing"
fi
if grep -q '^CONFIG_DEBUG_INFO_BTF=y' "$camera_tree/.config"; then
    command -v pahole >/dev/null || camera_fail "CONFIG_DEBUG_INFO_BTF requires pahole"
fi
echo "Configuration to preserve:"
grep -E '^CONFIG_(RUST|DRM_APPLE|DRM_ASAHI_M4|RUST_APPLE_RTKIT|VIDEO_APPLE_ISP|LOCALVERSION)=' "$camera_tree/.config" || true
if [[ $camera_failures == 0 ]]; then
    echo "Running kbuild's Rust availability check (no kernel Image build)."
    camera_check=$(make -C "$camera_tree" ARCH=arm64 LLVM=1 \
        "RUSTC=$camera_rustc" "HOSTRUSTC=$camera_hostrustc" "RUSTDOC=$camera_rustdoc" \
        "BINDGEN=$camera_bindgen" rustavailable 2>&1)
    camera_status=$?
    echo "$camera_check"
    [[ $camera_status == 0 ]] || camera_fail "kbuild rustavailable failed"
    [[ $camera_check != *"version does not match"* ]] || camera_fail "resolve the reported libclang/compiler version mismatch"
fi
if [[ $camera_failures != 0 ]]; then
    echo "RESULT: FAIL ($camera_failures checks); no installation or boot changes performed."
    exit 1
fi
echo "RESULT: PASS for build prerequisites; camera hardware and complete kernel build remain untested."
