# Builder images

These are the recipes for the Docker images that the build scripts and
`packaging/*-source-joins.json` name. They were recovered from each image's
history by the person who made the images, Kb2uka, in
[issue #180](https://github.com/kazuhidet/Omarchy-M4-Native/issues/180#issuecomment-6737887823).

**Status:** `m4-gravity-builder` was rebuilt from its recipe on 2026-11-10.
Its toolchain matched the recorded image exactly, and it reproduced the
display stage2 loaders byte for byte. See [Rebuild of 2026-11-10](#rebuild-of-2026-11-10).
The other two images have not been rebuilt.

Every `apt-get` line installs whatever is current in Ubuntu 26.04 when it runs,
so a rebuild's versions drift from the recorded image. Before using a rebuilt
image for any other output:
- compare it against [`m4-gravity-builder/packages.txt`](m4-gravity-builder/packages.txt);
- check that it reproduces that output's recorded hash.

## The images

All three are `linux/amd64` images. They start from the official
`ubuntu:26.04` (resolute) image, pinned by digest, and install only from
Ubuntu's archive, with no apt.llvm.org and no rustup. The apt sources are the
base image's defaults:
- `archive.ubuntu.com` for resolute, -updates and -backports;
- `security.ubuntu.com` for -security;
- all four components enabled.

| Image | Image ID | Recipe | Used by |
| --- | --- | --- | --- |
| `m4-gravity-builder:20261008` | `sha256:b2069edb8a23761d9211559fe632f5464aebc4cdfa9558d0f4c93211890fd7b1` | [`m4-gravity-builder/`](m4-gravity-builder/Dockerfile) | kernel, GPU, CPU, m1n1 and display loaders, and most source joins |
| `m4-gravity-mesa-arm-builder:20261008` | `sha256:ed20ced88326b460dde7e0f963d1589b78c438926fcecc37a5b4bd616dd8d9fd` | [`m4-gravity-mesa-arm-builder/`](m4-gravity-mesa-arm-builder/Dockerfile) | the `libevdi` library ([`display/evdi/`](../display/evdi/README.md)), cross-built for arm64 |
| `m4-gravity-builder:fullmodules-20261009` | `sha256:d94f6e0226dffce095eba2e7a3b059399473c9bbb03b5210a1834d4ba8e68ca2` | [`m4-gravity-builder-fullmodules/`](m4-gravity-builder-fullmodules/Dockerfile) | the alpha.1 AVD module rebuilds |

Notes on the recipes:
- **`m4-gravity-builder:20261008`:** the base image's first layer
  (`sha256:d6b1a90b…`, as recorded in #180) is also the builder's first layer.
- **`m4-gravity-mesa-arm-builder:20261008`:** it shares the base and the first
  two `RUN` lines with `m4-gravity-builder:20261008`.
- **`m4-gravity-builder:fullmodules-20261009`:** it is `m4-gravity-builder:20261008`
  plus `xz-utils`. The history records only the install command for
  `xz-utils`. The `apt-get update` before it and the cleanup after it follow
  the other lines.

The versions inside `m4-gravity-builder:20261008` are listed in full in
[`packages.txt`](m4-gravity-builder/packages.txt): 307 packages, from
`dpkg-query -W`. The ones that matter most:

| Tool | Version |
| --- | --- |
| clang, LLD | 21.1.8 (`clang-21`, `lld-21` at `1:21.1.8-6ubuntu1`; the `clang`, `lld` and `llvm` metapackages show `1:21.1.6-71`) |
| rustc, cargo | 1.93.1 (`1.93.1ubuntu1`, built against LLVM 21.1.8) |
| bindgen | 0.72.1 |
| gcc | 15.2.0 |
| libc6-dev | `2.43-2ubuntu2.4` |

`rust-src` is under `/usr/lib/rust-1.93/lib/rustlib/src`. `patch` and `file`
are not installed, as the build scripts note.

## Building and comparing

```sh
docker build --platform linux/amd64 -t m4-gravity-builder:20261008-rebuilt builders/m4-gravity-builder
docker run --rm --platform linux/amd64 m4-gravity-builder:20261008-rebuilt \
  dpkg-query -W -f '${Package}:${Architecture}=${Version}\n' |
  diff - builders/m4-gravity-builder/packages.txt
```

`packages.txt` is in `dpkg-query`'s own order, by package name, so compare the
output unsorted.

Tag a rebuilt image under a new name. The original names belong to the
recorded image IDs. An empty diff is the first condition for using a rebuild in
place of the original. The second is that it reproduces the recorded output
hashes. Ubuntu's snapshot archive for 2026-10-08 may be the way to pin the
versions, but that has not been tried.

## Rebuild of 2026-11-10

`m4-gravity-builder` was built from this directory, at commit `04eef50`, on a
native `linux/amd64` Docker host. It was built with
`docker build --platform linux/amd64` under the tag
`m4-gravity-builder:20261008-rebuilt`. Its image ID is
`sha256:f14995f4d22826337e4aec2e1908fdfff6db706d1d2587e1b5d0f8949421ca02`.
That differs from the recorded `b2069edb…`, as any later build does. Its first
layer is the same, `sha256:d6b1a90b…`.

**Packages.** It has the same 307 packages, in the same order, as
`packages.txt`. 289 have the same version.

The 18 others are updates published after 2026-10-08:

| Package | Recorded | Rebuild |
| --- | --- | --- |
| `ca-certificates` | `20260601~26.04.1` | `20260816ubuntu0.26.04.2` |
| `git`, `git-man` | `1:2.53.0-1ubuntu1` | `1:2.53.0-1ubuntu1.1` |
| `libbrotli1` | `1.2.0-3build1` | `1.2.0-3ubuntu0.1` |
| `libcurl3t64-gnutls`, `libcurl4t64` | `8.18.0-1ubuntu2.7` | `8.18.0-1ubuntu2.8` |
| `libgit2-1.9` | `1.9.1+ds-1ubuntu1.2` | `1.9.1+ds-1ubuntu1.3` |
| `libx11-6`, `libx11-data`, `libx11-dev` | `2:1.8.13-1` | `2:1.8.13-1ubuntu0.1` |
| `libxml2-16` | `2.15.2+dfsg-0.1ubuntu0.2` | `2.15.2+dfsg-0.1ubuntu0.3` |
| `linux-libc-dev` | `7.0.0-38.38` | `7.0.0-43.43` |
| `qemu-user`, `ubuntu-virt` | `1:10.2.1+ds-1ubuntu3.2` | `1:10.2.1+ds-1ubuntu3.3` |
| `ubuntu-helper-virt-hwe` | `1:10.2.1+ds-1ubuntu4.3` | `1:10.2.1+ds-1ubuntu4.4` |
| `tzdata` | `2026c-0ubuntu0.26.04.1` | `2026e-0ubuntu0.26.04.1` |
| `zlib1g`, `zlib1g-dev` | `1:1.3.dfsg+really1.3.1-1ubuntu3.1` | `1:1.3.dfsg+really1.3.1-1ubuntu3.2` |

**Toolchain.** The toolchain packages all have their recorded versions:
- `clang-21`, `lld-21`, `llvm-21` and `libllvm21`: `1:21.1.8-6ubuntu1`;
- `rustc`, `cargo` and `rust-src`: `1.93.1ubuntu1`;
- `bindgen`: `0.72.1-1`;
- `gcc-15`: `15.2.0-16ubuntu1`;
- `binutils`: `2.46-3ubuntu2`;
- `libc6-dev`: `2.43-2ubuntu2.4`.

Inside the image, the tools report `Ubuntu clang version 21.1.8 (6ubuntu1)`,
`Ubuntu LLD 21.1.8` and `rustc 1.93.1 (01f6ddf75 2026-02-11) (built from a
source tarball)`. `patch` and `file` are absent, as recorded.

**Output.** [`display/j713/build-backlight-loader.sh`](../display/j713/build-backlight-loader.sh)
was run in the rebuilt image, at commit `a55e412`, with alpha.1's
`m1n1-stage2-source.tar.gz` (`c3945179…`). All three stage2 loaders came out
byte-identical to the records:

| Loader | SHA-256 | Recorded as |
| --- | --- | --- |
| stock | `3a3f7a64c65fc366d5ac9aece3e1bee64119be012aa1ec5b15d2743c6f91fce4` | alpha.1's shipped stage2 (the script checks it) |
| backlight | `b86aee6840fe670b592271ec2816d42c5515cddc20a14e08bdc5bcbce547e6fd` | `stage2-hidden.bin` in `channel.json` |
| backlight-notch | `692f656cd8f6dfb2530172da518f9e2e18e6c5032df3062cd603eb4539e4c405` | `stage2-shown.bin` in `channel.json` |

The two published loaders' build evidence
(`packaging/channel-source-joins.json`) names
`m4-handoff-builder:amd64-rust93`, which has no recipe. This rebuild shows that `m4-gravity-builder` produces the
same bytes. Nothing else has been rebuilt in this image yet: not the kernel,
not the GPU or other modules, and not `libevdi`.

## Images without a recipe

The images that held these were no longer on the machine with the others, so
there is no history to recover them from:
- `m4-handoff-builder:amd64-rust93`, used for the backlight loader
  ([`display/j713/build-backlight-loader.sh`](../display/j713/build-backlight-loader.sh));
- `m4-dev-builder:clang21`, used for the native backlight module
  (`packaging/channel-source-joins.json`).

Their records name the same Ubuntu clang 21 toolchain family, so
`m4-gravity-builder` is the best starting point for either.
