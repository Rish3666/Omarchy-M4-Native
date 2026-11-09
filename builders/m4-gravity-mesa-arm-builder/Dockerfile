# SPDX-License-Identifier: MIT
# Copyright (c) 2026 KB2UKA
# m4-gravity-mesa-arm-builder:20261008, linux/amd64 with an arm64 cross toolchain
# Recovered from the image history by its author in issue #180; see builders/README.md.
# The base and the first two RUN lines are those of m4-gravity-builder:20261008.
FROM ubuntu:26.04@sha256:3131b4cc82a783df6c9df078f86e01819a13594b865c2cad47bd1bca2b7063bb
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends clang lld llvm make gcc libc6-dev libelf-dev libssl-dev flex bison bc python3 zstd cpio qemu-user proot ca-certificates git kmod && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends rustc rust-src cargo bindgen libclang-dev pkg-config libdrm-dev libwayland-dev wayland-protocols libx11-dev libxext-dev libxcb-dri3-dev libxcb-present-dev libxcb-randr0-dev libxcb-shm0-dev libxshmfence-dev libxxf86vm-dev libxrandr-dev libexpat1-dev libzstd-dev meson ninja-build python3-mako python3-yaml python3-packaging glslang-tools libclang-rt-dev && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends llvm-dev libclang-cpp-dev libllvmspirvlib-21-dev spirv-tools libclc-21-dev libclc-21 g++ libgtest-dev python3-ply libudev-dev bison flex && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends spirv-tools-dev && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends libwayland-egl-backend-dev && rm -rf /var/lib/apt/lists/*
RUN dpkg --add-architecture arm64 && sed -i '/^Types: deb$/a Architectures: amd64' /etc/apt/sources.list.d/ubuntu.sources && printf 'Types: deb\nURIs: http://ports.ubuntu.com/ubuntu-ports/\nSuites: resolute resolute-updates resolute-backports resolute-security\nComponents: main universe restricted multiverse\nArchitectures: arm64\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n' > /etc/apt/sources.list.d/m4-arm64.sources
RUN apt-get update && apt-get install -y --no-install-recommends g++-aarch64-linux-gnu libdrm-dev:arm64 libexpat1-dev:arm64 libzstd-dev:arm64 zlib1g-dev:arm64 libwayland-dev:arm64 libwayland-egl-backend-dev:arm64 libudev-dev:arm64 libelf-dev:arm64 && rm -rf /var/lib/apt/lists/*
