#!/bin/bash
# SPDX-License-Identifier: MIT
# Build an offline experimental artifact from a reviewed, already ported tree.
# No installation, initramfs regeneration, boot entry or firmware changes.
set -euo pipefail
[[ $# == 2 ]] || { echo "usage: $0 CLEAN_KERNEL_GIT_TREE NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
src=$(realpath "$1")
[[ ! -e $2 ]] || { echo "output already exists" >&2; exit 1; }
out=$(realpath -m "$2")
case "$out/" in "$src/"*) echo "output must be outside source tree" >&2; exit 1;; esac
[[ $(uname -m) == aarch64 ]] || { echo "native aarch64 build required" >&2; exit 1; }
for tool in make clang ld.lld llvm-ar llvm-nm llvm-objcopy bc bison flex openssl tar python3 xz; do
    command -v "$tool" >/dev/null || { echo "missing build dependency: $tool" >&2; exit 1; }
done
[[ $(git -C "$src" rev-parse --show-toplevel) == "$src" ]]
[[ -z $(git -C "$src" status --porcelain --untracked-files=normal) ]] || {
    echo "kernel tree must be clean and all source changes committed" >&2; exit 1;
}
[[ -f $src/.config ]] || { echo "supply the reviewed kernel .config" >&2; exit 1; }
if grep '^CONFIG_INITRAMFS_SOURCE=' "$src/.config" | grep -qv '^CONFIG_INITRAMFS_SOURCE=""$'; then
    echo "external built-in initramfs needs a separately reviewed asset manifest" >&2
    exit 1
fi
grep -q 'apple,t8132-isp' "$src/drivers/media/platform/apple/isp/isp-drv.c" || {
    echo "BLOCKED: source has no T8132 ISP support" >&2; exit 1;
}
mkdir -p "$2"
out=$(realpath "$2")
git -C "$src" rev-parse HEAD > "$out/source-commit"
git -C "$src" archive HEAD | tar -x -C "$out"
cp "$src/.config" "$out/.config"
cd "$out"
sha256sum .config > input-config.sha256
scripts/config --set-str LOCALVERSION '-omarchy-m4-camera-test' \
    --disable LOCALVERSION_AUTO --module VIDEO_APPLE_ISP
export KBUILD_BUILD_USER=builder KBUILD_BUILD_HOST=camera-test
export KBUILD_BUILD_TIMESTAMP="$(git -C "$src" show -s --format=%cD HEAD)"
export SOURCE_DATE_EPOCH="$(git -C "$src" show -s --format=%ct HEAD)"
# Check before olddefconfig can silently drop Rust and its dependent GPU driver.
rust_required=false
if grep -q '^CONFIG_RUST=y' .config; then
    rust_required=true
    for tool in "${RUSTC:-rustc}" "${RUSTDOC:-rustdoc}" "${BINDGEN:-bindgen}"; do
        command -v "$tool" >/dev/null || { echo "missing Rust dependency: $tool" >&2; exit 1; }
    done
    make ARCH=arm64 LLVM=1 rustavailable
fi
make ARCH=arm64 LLVM=1 olddefconfig
if "$rust_required" && ! grep -q '^CONFIG_RUST=y' .config; then
    echo "Rust support was lost; refusing a kernel that can break the M4 GPU" >&2
    exit 1
fi
release=$(make -s ARCH=arm64 LLVM=1 kernelrelease)
[[ $release == *-omarchy-m4-camera-test ]] || exit 1
make ARCH=arm64 LLVM=1 -j"${CAMERA_BUILD_JOBS:-$(nproc)}" Image modules dtbs
make ARCH=arm64 LLVM=1 INSTALL_MOD_PATH="$out/stage" DEPMOD=true modules_install
mkdir -p stage/kernel
cp arch/arm64/boot/Image stage/kernel/
cp arch/arm64/boot/dts/apple/t8132-j715.dtb stage/kernel/
cp .config source-commit stage/kernel/
find stage -type l \( -name build -o -name source \) -delete
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
    -cJf "linux-omarchy-m4-camera-test-$release.tar.xz" -C stage .
sha256sum "linux-omarchy-m4-camera-test-$release.tar.xz" > artifact.sha256
echo "Offline artifact only: $out/artifact.sha256"
