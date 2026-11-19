#!/bin/bash
set -euo pipefail
in=/in out=/out
source_sha=c394517941a5700b227718bb02e3df3dd43c9ad5a8e53c9447a55d3c36846c44
stock_sha=3a3f7a64c65fc366d5ac9aece3e1bee64119be012aa1ec5b15d2743c6f91fce4
hidden_sha=b86aee6840fe670b592271ec2816d42c5515cddc20a14e08bdc5bcbce547e6fd
tag=air-c9ef56f-gpu-stage2-20261008
export PATH=/usr/lib/llvm-21/bin:$PATH
mkdir -p $out
tree=/job/bootloader-air-knownbase-stage2
build() {
    local kind=$1 version=$2
    rm -rf "$tree"; mkdir -p "$tree"
    tar xzf $in/m1n1-stage2-source.tar.gz -C "$tree" --strip-components=1
    rm -rf "$tree/build"
    if [ "$kind" != stock ]; then cp $in/m1n1-base/src/{kboot.c,dart.c,dart.h} "$tree/src/"; fi
    if [ "$kind" = ispd ]; then cp $in/ispd/kboot.c "$tree/src/"; fi
    ( cd "$tree"; export M1N1_VERSION_TAG=$version
      for pass in 1 2; do
        make BUILDSTD=1 USE_CLANG=1 TOOLCHAIN=/usr/lib/llvm-21/bin/ LLDDIR=/usr/lib/llvm-21/bin/ RELEASE=1 CHAINLOADING=0 NO_DISPLAY=1 -j8
      done
      cat build/build_cfg.h build/build_tag.h ) > $out/stage2-$kind-build.log 2>&1
    cp "$tree/build/m1n1.bin" $out/stage2-$kind-m1n1.bin
    rm -rf "$tree"
}
test "$(sha256sum < $in/m1n1-stage2-source.tar.gz | cut -d' ' -f1)" = "$source_sha"
build stock "$tag"
test "$(sha256sum < $out/stage2-stock-m1n1.bin | cut -d' ' -f1)" = "$stock_sha" || { echo STOCK-MISMATCH; exit 1; }
build backlight "$tag-backlight1"
test "$(sha256sum < $out/stage2-backlight-m1n1.bin | cut -d' ' -f1)" = "$hidden_sha" || { echo HIDDEN-MISMATCH; exit 1; }
build ispd "$tag-backlight1-isphandoff1"
cd $out && sha256sum ./*.bin && ls -l ./*.bin
echo BUILD-OK
