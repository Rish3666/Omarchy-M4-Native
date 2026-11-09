# SPDX-License-Identifier: MIT
# Copyright (c) 2026 KB2UKA
# m4-audio-daemon-arm-builder (sha256:aca411d1df20ffd305e9d470b47e919afa47819e65f2654b757d93a15ddf5506), linux/amd64
# Retained in alpha.1's j713-audio-reconstruction.tar as toolchain/daemon-arm64-builder.Dockerfile;
# see builders/README.md. It builds the speaker daemon and the VA-API driver for aarch64.
FROM m4-gravity-mesa-arm-builder:20261008
RUN printf 'Types: deb\nArchitectures: arm64\nURIs: http://ports.ubuntu.com/ubuntu-ports/\nSuites: resolute resolute-updates resolute-security\nComponents: main universe restricted multiverse\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n' > /etc/apt/sources.list.d/arm64.sources && apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libstd-rust-dev:arm64 libasound2-dev:arm64 pkg-config
