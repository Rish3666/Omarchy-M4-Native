# Builder images

These are the recipes for the Docker images that the build scripts and
`packaging/*-source-joins.json` name. They were recovered from each image's
history by the person who made the images, Kb2uka, in
[issue #180](https://github.com/kazuhidet/Omarchy-M4-Native/issues/180#issuecomment-6737887823).

**Status: no image has been rebuilt from these recipes yet.** Every `apt-get`
line installs whatever is current in Ubuntu 26.04 when it runs, which will not
be exactly the versions the images hold. Until a rebuild has been compared
against [`m4-gravity-builder/packages.txt`](m4-gravity-builder/packages.txt) and
the recorded output hashes, do not claim byte-identical output from a rebuilt
image.

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

## Images without a recipe

The images that held these were no longer on the machine with the others, so
there is no history to recover them from:
- `m4-handoff-builder:amd64-rust93`, used for the backlight loader
  ([`display/j713/build-backlight-loader.sh`](../display/j713/build-backlight-loader.sh));
- `m4-dev-builder:clang21`, used for the native backlight module
  (`packaging/channel-source-joins.json`).

Their records name the same Ubuntu clang 21 toolchain family, so
`m4-gravity-builder` is the best starting point for either.
