# SPDX-License-Identifier: MIT
# Copyright (c) 2026 KB2UKA
# m4-gravity-builder:20261008, linux/amd64
# Recovered from the image history by its author in issue #180; see builders/README.md.
FROM ubuntu:26.04@sha256:3131b4cc82a783df6c9df078f86e01819a13594b865c2cad47bd1bca2b7063bb
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends clang lld llvm make gcc libc6-dev libelf-dev libssl-dev flex bison bc python3 zstd cpio qemu-user proot ca-certificates git kmod && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends rustc rust-src cargo bindgen libclang-dev pkg-config libdrm-dev libwayland-dev wayland-protocols libx11-dev libxext-dev libxcb-dri3-dev libxcb-present-dev libxcb-randr0-dev libxcb-shm0-dev libxshmfence-dev libxxf86vm-dev libxrandr-dev libexpat1-dev libzstd-dev meson ninja-build python3-mako python3-yaml python3-packaging glslang-tools libclang-rt-dev && rm -rf /var/lib/apt/lists/*
