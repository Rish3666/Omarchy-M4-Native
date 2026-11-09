# Builder images

These are the recipes for the Docker images that the build scripts and
`packaging/*-source-joins.json` name. They were recovered from each image's
history by the person who made the images, Kb2uka, in
[issue #180](https://github.com/kazuhidet/Omarchy-M4-Native/issues/180#issuecomment-6737887823).

**Status:** all three images were rebuilt from these recipes on 2026-11-10.
`m4-gravity-builder`'s toolchain matched the recorded image exactly. The
rebuilt images reproduced every recorded output that was tried, 27 distinct
files, byte for byte. See [Rebuild of 2026-11-10](#rebuild-of-2026-11-10) and
[Outputs rebuilt on 2026-11-10](#outputs-rebuilt-on-2026-11-10).

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
same bytes.

## Outputs rebuilt on 2026-11-10

The other two images were rebuilt the same day from this directory, at commit
`b974780`:

| Image | Rebuilt as | Image ID |
| --- | --- | --- |
| `m4-gravity-mesa-arm-builder:20261008` | `m4-gravity-mesa-arm-builder:20261008-rebuilt` | `sha256:214e94f058cae290bc752b70c2511b12fea305546155f8b0b3c95e209daefdab` |
| `m4-gravity-builder:fullmodules-20261009` | `m4-gravity-builder:fullmodules-20261009-rebuilt` | `sha256:fbf66f09a63370743c11e9bc1659ff2b5560334b5fe494d6cfc5b750eafbba42` |

Neither has a recorded package manifest to compare against. Their cross
compiler is `aarch64-linux-gnu-gcc` 15.2.0 (`15.2.0-16ubuntu1`), and the
fullmodules image has `xz-utils` `5.8.3-1ubuntu0.1`.

**How the outputs were built.** Each output below was built in a rebuilt image
with the repository's own script, or with the recipe its records give. The
inputs were alpha.1's published source assets, checked against their pinned
hashes:
- `kernel-controller.tar.gz` (`810339d8…`);
- `kernel-decoder.tar.gz` (`13b89bb0…`);
- `build-inputs-final.tar.gz` (`6a800de1…`);
- `reference-sound-exports.symvers` (`9f3e2cf8…`);
- `m1n1-stage1-source.tar.gz` and `m1n1-stage2-source.tar.gz`;
- the alpha.1 Air GPU source packet (`c19a7c97…`);
- `evdi-1.15.1.tar.gz` (`b120df30…`).

The kernel modules were built with `--network none`. The m1n1 loaders need
the network for their Rust crates, and were built as root, as their scripts
say. For each, the build directory and the kernel tree were at the paths the
records use: `/job`, `/kernel`, and `/job/kernel-air-bootstrap`. Those paths
end up in some outputs.

**Results.** All 27 distinct outputs came out byte-identical. The audio
modules `apple-admac.ko`, `snd-soc-macaudio.ko` and `snd-soc-tas2764.ko` are
the same file whether they are built from today's `audio/j713/kernel` or from
alpha.1's (`ee98743a`). Each is listed once below.

| Output | Built with | SHA-256 | Recorded in |
| --- | --- | --- | --- |
| stage2 stock, backlight, backlight-notch | `display/j713/build-backlight-loader.sh` | see the table above | `channel.json`, alpha.1 |
| stage2 notch | `display/j713/build-notch-loader.sh` | `f2417a74d13838004847a6fbdf946b524005301b88b5a403b1e79cb36d0ec7ca` | `tools/m4-notch.py`, `docs/package-channel.md` |
| stage1 stock (alpha.1) | `patches-m1n1/build-test-loaders.sh` | `18cc4cd1ba07928078d2cb52a2c1c5f40a4661fd3db7ee6af0e6923fd237be10` | `docs/j713-m1n1-issue82-ans-reset.md` |
| stage1 `ans1` | same | `8c5a15736c19d0a3428e64f01292791fb54dd68e09f2f5304a7210d19c42adce` | same |
| stage1 `dctx1-ans1` | same | `77881a4c673c08c58e270b0adfa923701ddc538a072f7b2e3825e5faaa2aaec8` | same |
| `j713_cpuidle.ko` | `cpu/j713/build-module.sh` | `a2a7947a1d2260abcfc6eb10d7d63643ad2e191e73e93fedddf605116cdfd5a9` | `channel.json` |
| `j713_pguard.ko` | same | `91fe247e7e83d30f62f35bcf64ddbcb42faa3a1c109881d5aefcb64dc7e5e691` | `channel.json` |
| `evdi.ko` | `display/evdi/build.sh module` | `c5e65a2bcba6433ff8369fea449ccc4e6be178a392b9c4a959884415953c671a` | `channel.json` |
| `libevdi.so.1.15.1` (mesa-arm image) | `display/evdi/build.sh library` | `0f1da52db1f7cbd7e0c420d47285ddee78e22dc0a57e789305c1456b163034ce` | `channel.json` |
| `asahi_m4.ko` (alpha.1) | `gpu/j713/build-test-module.sh` | `80cf3669575edd09aed226a93e47aaaf132e70f1070154629c413c0b40d34578` | `release-source-joins.json` |
| `asahi_m4.ko` (current `g16.rs`) | same | `de0337a773930c7862a99706112dd71eaaecf2021707da248fd3d07feefdc824` | `channel.json` |
| `j713_hp_dt.ko` | `tools/build-j713-headphones.sh` steps | `3f501c6193aeddc62031395e899909bf352851278f829458998ca1c4dbbe6149` | `channel.json` |
| `snd-soc-j713-headphones.ko` | same | `2e743937b4bd8315ec6dba6bef4bbfbf197d4bf6f8688761954579192df48244` | `channel.json` |
| `snd-soc-j713-group.ko` (current) | `tools/build-j713-audio.sh` kernel steps | `aaad802eb136ff6cb915feaa123001b3eb848bc2f038d0a5b71c8e2ff35d2581` | `channel.json` |
| `snd-soc-apple-mca.ko` (current) | same | `fb941df4d55c4f2093b4595e0392aaf97ffe3a250228518b18a4f70568bf7454` | `channel.json` |
| `snd-soc-j713-group.ko` (alpha.1) | same, at `ee98743a` | `465a88aa9f70ceac8682499ad6bd9ecd34a33b35a3b5c556b42f7bd1524272d0` | `release-source-joins.json` |
| `snd-soc-apple-mca.ko` (alpha.1) | same, at `ee98743a` | `d3194660a28d30ba8ea296b6592836ad4ca9426d9471d05ba8ce3cad284baa1e` | `release-source-joins.json` |
| `j713_audio_bootstrap.ko` (alpha.1) | same, at `ee98743a` | `1bf6408c629f446e8d73b6962ef58c2a98a3c7ecd5f7b7ae001bcd5bab6c1875` | `release-source-joins.json` |
| `j713_audio_dt3.ko` (alpha.1) | same, at `ee98743a` | `0b115a55e3aaccad6f148ee152c399c403c8ebcbcbf01f22210e33484c166e4e` | `release-source-joins.json` |
| `apple-admac.ko` | same | `cd57f99657e6232e45d58645949a0f73b656372d92e272828c14bcd4e63ea110` | `release-source-joins.json` |
| `snd-soc-macaudio.ko` | same | `1dc3a6878b10154676b1b06529b197baf3b1cf1c81b5ef94128b2f52d605ea34` | `release-source-joins.json` |
| `snd-soc-tas2764.ko` | same | `dc00caabad80dffe95e872222440a4711ca57a37bd4271ae08e971e22d7d15f7` | `release-source-joins.json` |
| `j713_dcp_backlight.ko` | `tools/build-j713-backlight.sh` | `2186b280cce0c321b204cfda0cf65d221e42cc63b97b7b884ac31b5999a8e390` | `channel.json` |
| `avd-controller.ko` (fullmodules image) | `recipe/BUILD.md` in `build-inputs-final.tar.gz` | `ade00c8882ccc32aa8480eba13e9232f3765ba3a461942d2967c22beb7d5ab2d` | `release-source-joins.json` |
| `apple-avd.ko` (fullmodules image) | same | `89ff8a98cd971392e1ec9d8b6c2b74ff09669e0c681ef35eee4d447aabad9fba` | `release-source-joins.json` |

Notes:
- **Paths.** `apple-avd.ko` embeds the paths of two kernel headers. It came
  out different (`bac8a4ba…`) when the decoder tree was unpacked anywhere but
  `/kernel`, where `recipe/BUILD.md` mounts it. With the tree at `/kernel` it
  matched. `.text` was the same in both; only `.rodata` and its relocations
  differed.
- **The scripts that run Docker themselves.** These are
  `tools/build-j713-audio.sh` and `tools/build-j713-headphones.sh`. Their
  kernel steps were run inside the image, without the scripts' own
  `docker run`, because the Docker host was remote and could not bind-mount
  local paths. The steps were the same: the `kernel-inputs.sha256` check
  before and after, the exports hash, and the same `make` line.
- **Images without a recipe.** The records name them for two of these
  outputs: `m4-dev-builder:clang21` for `j713_dcp_backlight.ko`, and
  `m4-handoff-builder:amd64-rust93` for the stage2 loaders. Both outputs came
  out identical from `m4-gravity-builder`.
- **Not rebuilt here:**
  - the kernel `Image`, which no record claims byte-identical;
  - Mesa and the VA-API driver, MIT userspace whose joins are `unverified`;
  - the speaker daemon.

## Images without a recipe

The images that held these were no longer on the machine with the others, so
there is no history to recover them from:
- `m4-handoff-builder:amd64-rust93`, used for the backlight loader
  ([`display/j713/build-backlight-loader.sh`](../display/j713/build-backlight-loader.sh));
- `m4-dev-builder:clang21`, used for the native backlight module
  (`packaging/channel-source-joins.json`).

Their records name the same Ubuntu clang 21 toolchain family. The outputs
their records name came out byte-identical from `m4-gravity-builder` (see
[Outputs rebuilt on 2026-11-10](#outputs-rebuilt-on-2026-11-10)), so use
`m4-gravity-builder` in place of either.
