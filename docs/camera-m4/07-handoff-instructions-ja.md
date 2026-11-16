# J715 内蔵カメラ開発・ビルド VM 引継ぎ指示書

作成日: 2026-11-16。対象は **M4 MacBook Air 15-inch / Mac16,13 / J715AP / T8132**。
最初に本書を読み、`08-handoff-package.md` で実際に同梱したファイルとコピー結果を確認する。

## 1. 今回の依頼と引継ぎの目的

目標は、既存 Omarchy 環境を維持しながら内蔵カメラで Linux の実フレームを取得し、
V4L2 / PipeWire / ブラウザーで利用できるようにすること。
この引継ぎでは **macOS は実機情報採取と VM ホスト、ビルドは aarch64 Arch Linux（Omarchy）VM** と分担する。
macOS のシェルで Linux 用ビルドスクリプトを直接実行しない。

ユーザー確認済みの VM ツールチェーンは **Clang 21.1.8、rustc 1.93.1**。
以前の「bindgen と rust-src 不足」はこの対話のローカル Linux 環境での確認であり、
ユーザーのビルド VM で不足していると確認したわけではない。VM は下記 preflight で実際に検査する。

## 2. これまでの依頼・取得済み資料

| 順序 | 依頼・確認 | 結果 |
|---|---|---|
| 1 | j715-Camera-Task.md の実行 | 環境調査、上流解析、移植、隔離ビルド補助と文書を作成 |
| 2 | 上流取得エラーの URL 確認・訂正 | この実行環境の名前解決失敗を一般の DNS 制限と断定した点を訂正 |
| 3 | linux-aurora clone と PR fetch | ユーザーが clone / #421 / #422 fetch を実施、ローカルソースで解析 |
| 4 | macOS の初回情報採取 | macos-version、system-profiler、IODeviceTree、IOService の4ファイル取得済み |
| 5 | カメラ動作ログの追加採取 | 初回手順に不足していたため追加依頼。live log / stderr / 撮影中 IORegistry を取得済み |
| 6 | 表示灯の実機観察 | カメラセンサーエリア LED が使用中点灯し、使用後消灯したとのユーザー報告 |
| 7 | ビルド場所の明確化と本書作成 | macOS + aarch64 Arch VM、Clang 21.1.8 / Rust 1.93.1 を基準に整理 |

元の依頼全文は引継ぎセットの `j715-Camera-Task.md`。
raw macOS 資料は Transfer 上の `j715-camera-inspection/` に既にある。再採取は原則不要。
raw ログ・IORegistry には個体情報が含まれ得るため公開 Git に追加しない。

## 3. 現在の到達点

| 機能・検証 | 状態 | 実際に確認した範囲 |
|---|---|---|
| J715/T8132 識別 | WORKING | Linux DT / macOS の識別情報 |
| センサー識別 | WORKING | firmware log の sensorID=0x958 と IMX958 の両方 |
| macOS indication | WORKING（ユーザー観測） | センサーエリア LED の使用中点灯・終了後消灯 |
| ISP/DART リソース | PARTIAL | 実機 ADT のアドレス・IRQ・13 DAPF 範囲を確認 |
| T8132 ISP 移植 | IMPLEMENTED / UNTESTED | 通常版・KUnit 込み module compile/link、実機初期化なし |
| DART static remap backport | IMPLEMENTED / UNTESTED | unlocked DART 向け、通常版・KUnit 込み compile/link |
| DT 草案・preview | IMPLEMENTED / UNTESTED | disabled resource fragment と提案 crop の dtc 検証 |
| Python 回帰 | WORKING | 現時点16件通過 |
| KUnit 実行 | NOT IMPLEMENTED（実行未実施） | test source はビルド済み、実行結果はまだない |
| フル Image / module 一式 | 未検証 | VM で今回の camera series をフルビルドしていない |
| Linux 表示灯・初期化・撮影 | BLOCKED | 正しい ISP DT / firmware handoff / setfile revision / indicator 制御が未確定 |
| PipeWire / ブラウザー / suspend | BLOCKED | Linux 実フレームと表示灯の検証後に行う |

現在のカーネルは `7.1.9-m4-gpu-backport-20261008`、build #16。
既存 kernel/modules/boot entry は変更・上書きしていない。
補助ビルドで生成した旧 release の .ko は compatibility 試験用で、インストール用ではない。

## 4. 調査で確定したこと・残る未知

- macOS 27.2.1（26B131）、ISP firmware 6.105。
- ISP MMIO は 0x48c000000 / 0x3ff0000、補助領域は 0x380700000 / 0x18000。
- ISP IRQ の列は 369/370/371/372/382。どれをどう mailbox に割り当てるかは未確定。
- DART は 0x48e8c0000 / 0x48e8e0000 / 0x48e900000（各 0xc000）、IRQ 387。
- DAPF instance 0 は ADT reg[5]、0x48e8d0000 / 0x4000。13範囲は上流 T8132 と一致。
- stream は0と12、remap source は1/2/3/6/7/10/11。VM base 0x10000000000、size 0xe0000000。
- IMX958 は config 6、raw 3040x5760 / processed region 3040x2880。fps=30 は要求値であり実測値ではない。
- firmware の物理配置は macOS boot 時の値。**Linux reserved-memory へそのまま固定しない**。
- ADT で virtual とされる ISP power state の zero offset をレジスターにしない。
- mailbox/gpio の分割、power/clock の全依存、Linux boot の firmware text/data/heap 予約が残る。
- setfile の候補 2224_01 / 2226_02 は同じ IMX958 に対応する。センサー一致だけで module/revision は決まらない。
- macOS の LED 観測だけで hardware interlock や Linux の制御方法を証明したことにはならない。

詳細と数値の出所は `03-hardware-identification.md` と `j715-resource-summary.json`。
公開用 summary から raw serial/calibration と firmware 物理配置を除外している。

## 5. ソース・パッチの対応

開発対象は Omarchy-M4-Native、ブランチ `camera/j715-isp-bringup`。
`patches-kernel/j715-camera/series` の順番を変えずに適用する。

| 順序 | ファイル | 内容 |
|---|---|---|
| 1 | 0001-isp-h17-prerequisites.patch | 固定 Aurora snapshot の汎用 H17 前提 |
| 2 | 0002-isp-t8132-upstream.patch | PR #421 の ISP 部分、T8132 / DAPF / firmware restore / 電源停止等 |
| 3 | 0003-j715-block-unverified-capture.patch | J715 は firmware 起動前の STREAMON を -EACCES で拒否 |
| 4 | 0004-isp-copy-payload-within-message-object.patch | IPC payload の FORTIFY 警告修正、メッセージ境界を保持 |
| 5 | 0005-dart-static-stream-remaps.patch | unlocked DART の static remap、入力検証・locked-root 拒否・KUnit |

確認済み上流:

- integration: `39d5f88ab4e54bb61eecd3fba79e3242005f2f76`
- PR #421: `af2676a9ee596bc94bb016d52a925ce550c46963`
- PR #422: `8916070002f4dc60e1bca6995b9c52fa0131683f`
- T8132: `5f3511a0e7e93395a83273946947e84cb93bf593`
- DAPF: `00e88f127ec23bee3605e54c7bd9338ff022980f`
- T8132 電源停止: `a17e540a0df57cb4b304b15212a5f3eb5de45037`
- DART remap の参照: `f57d9004043387ed6c437ddf0afcfcc1bb49f2fd`
- installer #208: `cffff8b5ed2cbaa8dd52233188251e9d3791ef85`（Web 確認。Git ソース取得・全レビューは未完了）

#422 の M5 GPIO / watchdog / firmware 物理配置は J715 へ移植していない。
DART backport は upstream 全体の置換ではない。locked root への新規 remap は -EOPNOTSUPP。
実機 DART の lock/version/TLB と回帰は今後の確認対象。

## 6. 必要な環境

### macOS 実機

J715 の通常 macOS 起動、ターミナル、`ioreg` / `log` / `system_profiler` / `shasum` / `tar`。
ログ採取に管理者権限を使ったが、NVRAM / EFI / firmware の変更は不要。
取得済み7ファイルはそのまま保存する。写真や動画の追加提出は現段階では不要。

### ビルド VM（確認済みの構成を維持）

| 項目 | 必要条件 |
|---|---|
| OS/CPU | aarch64 Arch Linux（Omarchy）。VM 内の Linux filesystem で作業 |
| C/LLVM | clang / LLD / llvm-ar / nm / objcopy / objdump / strip は21.1.8系で統一 |
| Rust | rustc / HOSTRUSTC / rustdoc は1.93.1。既存 PATH または明示した実行パス |
| Rust source | 同じ1.93.1の standard library source。core/src/lib.rs が存在すること |
| bindgen | 基準は元 config にある0.72.1。別版は kbuild と libclang の互換性確認が必要 |
| libclang | bindgen が利用する版を21.1.8に合わせる。必要なら VM の LIBCLANG_PATH を指定 |
| 基本コマンド | git, make, bash, patch, Python3, bc, bison, flex, pkg-config, perl |
| build/packaging | OpenSSL と libelf の開発環境、cpio, rsync, kmod/depmod, GNU tar, xz, coreutils |
| DT | kbuild の dtc。単独検証には VM の dtc を利用してもよい |
| BTF | CONFIG_DEBUG_INFO_BTF=y の場合のみ pahole も必要 |
| 資源の目安 | 4～8 vCPU、RAM16GiB、空き80GiBを提案。実際の所要量・時間は未測定 |
| test VM | KUnit 実行には今回の kernel と modules が一致する、破棄可能な ARM64 VM が別途必要 |

exFAT / macOS の共有領域を kernel build directory にしない。大文字小文字・symlink・permission を保つ。
パッチと圧縮 archive は Transfer に置き、展開・コンパイルは VM 内で行う。
既存の Clang21/Rust1.93 を最新版へ一括置換しない。現在の Arch の rust-src を無条件に追加すると
Rust1.93 と版が異なる可能性があるため、対応版の component/source を選ぶ。
`/usr/lib/rust-1.93` は過去の Ubuntu builder の履歴で、Arch VM の必須パスではない。

## 7. 引継ぎセットの展開と整合性

以下は ARM64 Linux VM の bash。macOS では checksum コマンドを `shasum -a 256 -c` に置き換えられる。

```bash
sha256sum -c j715-camera-handoff-20261116.tar.gz.sha256
tar -xzf j715-camera-handoff-20261116.tar.gz
cd j715-camera-handoff-20261116
sha256sum -c SHA256SUMS
export CAMERA_HANDOFF_ROOT="$PWD"
export CAMERA_PROJECT="$CAMERA_HANDOFF_ROOT/project"
export CAMERA_WORK="$HOME/Work/j715-camera-vm"
mkdir -p "$CAMERA_WORK/logs" "$CAMERA_WORK/artifacts"
set -euo pipefail
```

`project/` は固定 commit のソース snapshot。Git 履歴を使う場合は別の新規ディレクトリへ:

```bash
git clone -b camera/j715-isp-bringup "$CAMERA_HANDOFF_ROOT/project.bundle" "$CAMERA_WORK/project-git"
```

project の commit は `PROJECT-COMMIT.txt`、各 archive の checksum は `SHA256SUMS` にある。
この文書を読んでいるだけで Transfer へのコピーが済んだとは扱わない。実際の成否は `08-handoff-package.md` に記録する。

## 8. kernel base の選択・事前検査

第一候補は VM で従来ビルドに使っていた、M4 backport を含む **7.1.9 のソースの隔離コピー**。
その ISP/DART source hash が今回の manifest と一致しなければ作業を止める。
最新 Aurora kernel 全体に切り替えて M4 GPU/audio の互換性を仮定しない。

代替として同梱したローカル source snapshot を使う場合:

```bash
tar -xJf "$CAMERA_HANDOFF_ROOT/inputs/kernel-base-7.1.9-camera-reference.tar.xz" -C "$CAMERA_WORK"
export CAMERA_BASE="$CAMERA_WORK/kernel-base"
```

この snapshot には `.config` を戻してある。生成済み鍵・ELF・cache を除去したもので、
完全な upstream Git checkout ではない。Documentation/Makefile が元から省略され、通常の mrproper は失敗する。
作成側のコピーで recursive clean を避けて生成物を除去した経緯は `inputs/BASE-CLEANUP.json`。
**この参考 snapshot では再度 mrproper を実行せず、新しい archive 展開からやり直す。**
未確認の不足ファイルが出たら、そのログを保存して VM の既知の完全ソースと比較する。
フルビルド成功を保証した archive ではない。

VM の既存ソースを使う場合も、元ツリー・設定を上書きせずコピーを作り、
そのコピーに `inputs/base.config` を置いて CAMERA_BASE を指定する。
VM 自身の generic kernel config と M4 実機用 config を混同しない。

```bash
bash "$CAMERA_PROJECT/tools/camera-m4-vm-preflight.sh" "$CAMERA_BASE" 2>&1 | tee "$CAMERA_WORK/logs/vm-preflight.log"
```

FAIL のまま先へ進まない。この対話環境での FAIL 記録は VM の結果ではない。
標準と異なる compiler path は RUSTC / HOSTRUSTC / RUSTDOC / BINDGEN として preflight に指定できる。
Rust source の場所が標準 sysroot と違う場合は、対応1.93.1の `library/` を RUST_LIB_SRC に指定する。
rustup で1.93.1を管理している場合に限り、同じ toolchain の rust-src component を追加する方法もある。
配布パッケージ管理と rustup を混ぜず、実際に使う compiler/source の対応を記録する。

## 9. パッチ適用と offline テスト

```bash
python3 "$CAMERA_PROJECT/tools/prepare-j715-camera.py" "$CAMERA_BASE" "$CAMERA_WORK/kernel-camera" \
  2>&1 | tee "$CAMERA_WORK/logs/prepare.log"
export CAMERA_TREE="$CAMERA_WORK/kernel-camera"
cd "$CAMERA_PROJECT"
python3 -m unittest discover -s tests -p 'test*camera*.py' -v \
  2>&1 | tee "$CAMERA_WORK/logs/python-tests.log"
bash -n tools/camera-m4-fetch.sh tools/build-j715-camera.sh tools/camera-m4-vm-preflight.sh
```

現時点の期待値は Python16件成功。prepare は元 source を変更せず、base hash と5パッチの最終 hash を検査する。
hash mismatch を --force、fuzz、手修正で回避しない。異なる base の差分を先にレビューする。
出力の `camera-preparation.json` は artifact とともに保管する。

## 10. フル kernel ビルド（VM、現在は実機撮影不可の開発ビルド）

以降は既存の toolchain が PATH で選ばれていることを確認して実行する。
Makefile は RUSTC 等を独自に代入するため、非標準パスは単なる export に頼らず make 引数にも渡す。

```bash
export CAMERA_RUSTC_BIN="$(command -v rustc)"
export CAMERA_RUSTDOC_BIN="$(command -v rustdoc)"
export CAMERA_BINDGEN_BIN="$(command -v bindgen)"
camera_make=(make ARCH=arm64 LLVM=1 "RUSTC=$CAMERA_RUSTC_BIN" \
  "HOSTRUSTC=$CAMERA_RUSTC_BIN" "RUSTDOC=$CAMERA_RUSTDOC_BIN" "BINDGEN=$CAMERA_BINDGEN_BIN")
cd "$CAMERA_TREE"
cp .config "$CAMERA_WORK/artifacts/camera-config-before-olddefconfig"
"${camera_make[@]}" rustavailable 2>&1 | tee "$CAMERA_WORK/logs/rustavailable.log"
```

署名設定が元の基準と異なる場合は、以下の公開証明書手順を実行せず既存の署名手順を確認する。
今回の基準では MODULE_SIG_ALL / FORCE は有効になっていない。新たに無効化して通す手順ではない。

```bash
if grep -Eq '^CONFIG_MODULE_SIG_(ALL|FORCE)=y' .config; then
  echo 'STOP: preserve and review the existing module-signing workflow' >&2
  exit 1
fi
cp "$CAMERA_HANDOFF_ROOT/inputs/base-signing-certificate.pem" certs/signing_key.pem
if grep -q 'PRIVATE KEY' certs/signing_key.pem; then exit 1; fi
printf '%s\n' 'savedcmd_certs/signing_key.pem := openssl req -new -nodes -utf8 -sha512 -days 36500 -batch -x509 -config certs/x509.genkey -outform PEM -out certs/signing_key.pem -keyout certs/signing_key.pem  2>&1' \
  > certs/.signing_key.pem.cmd
"${camera_make[@]}" olddefconfig 2>&1 | tee "$CAMERA_WORK/logs/olddefconfig.log"
python3 scripts/diffconfig "$CAMERA_WORK/artifacts/camera-config-before-olddefconfig" .config \
  | tee "$CAMERA_WORK/logs/config.diff"
grep -E '^CONFIG_(RUST|DRM_APPLE|DRM_ASAHI_M4|RUST_APPLE_RTKIT|VIDEO_APPLE_ISP|LOCALVERSION)=' .config
```

公開証明書は元ローカル source の PEM から証明書だけを取り出し、元 DER との一致を確認したもの。
秘密鍵は同梱しない。元 running Image と source の完全一致を証明した、という意味ではない。
既存 `tools/build-j715-kernel.sh` の公開証明書再利用方式を参照した。
Rust/GPU/audio/入力/SSD の有効設定が意図せず落ちたら停止し、Rust を無効化して進めない。
new test option の追加や compiler metadata と、デバイス機能の喪失を区別して config.diff をレビューする。

```bash
export KBUILD_BUILD_USER=builder
export KBUILD_BUILD_HOST=j715-camera-vm
export KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP='2026-11-16 00:00:00 UTC'
export SOURCE_DATE_EPOCH=1794787200
export CAMERA_JOBS=4
CAMERA_RELEASE=$("${camera_make[@]}" -s kernelrelease)
case "$CAMERA_RELEASE" in *-omarchy-m4-camera-test) ;; *) echo 'unexpected kernel release'; exit 1;; esac
"${camera_make[@]}" -j"$CAMERA_JOBS" Image modules dtbs 2>&1 | tee "$CAMERA_WORK/logs/kernel-build.log"
export CAMERA_STAGE="$CAMERA_WORK/stage-$CAMERA_RELEASE"
test ! -e "$CAMERA_STAGE"
"${camera_make[@]}" INSTALL_MOD_PATH="$CAMERA_STAGE" DEPMOD=true modules_install \
  2>&1 | tee "$CAMERA_WORK/logs/modules-stage.log"
mkdir -p "$CAMERA_STAGE/kernel"
cp arch/arm64/boot/Image arch/arm64/boot/dts/apple/t8132-j715.dtb .config camera-preparation.json "$CAMERA_STAGE/kernel/"
find "$CAMERA_STAGE" -type l \( -name build -o -name source \) -delete
printf '%s\n' "$CAMERA_RELEASE" > "$CAMERA_STAGE/kernel/kernelrelease.txt"
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
  -cJf "$CAMERA_WORK/artifacts/linux-$CAMERA_RELEASE.tar.xz" -C "$CAMERA_STAGE" .
sha256sum "$CAMERA_WORK/artifacts/linux-$CAMERA_RELEASE.tar.xz" \
  > "$CAMERA_WORK/artifacts/linux-$CAMERA_RELEASE.tar.xz.sha256"
```

`modules_install` は stage のみ、depmod の実機実行も行わない。VM や実機の /boot /usr/lib/modules へは入れない。
この tar は導入用の署名済み Arch package / initramfs / m1n1 chain ではない。
現在の DT には完全な ISP node がなく、撮影ガードもあるため、ビルドしてもカメラ利用開始にはならない。
`build-j715-camera.sh` は完全な clean Git kernel snapshot を入力にする別の補助であり、
Git 管理されていない今回の参考 source へそのまま向けない。本書では上記の明示的な手順を基準とする。
バイト一致再現には toolchain / Rust metadata の絶対パス等も固定する必要があり、現時点では未達成。

### DT 草案の単独コンパイル（full build 後の dtc を利用）

production board を編集せず、test wrapper だけで確認する。

```bash
mkdir -p "$CAMERA_WORK/dt-test"
cat > "$CAMERA_WORK/dt-test/j715-camera-resources.dts" <<EOF
#include "$CAMERA_TREE/arch/arm64/boot/dts/apple/t8132-j715.dts"
#include "$CAMERA_PROJECT/dts/camera-m4/t8132-j715-dart-resources.dtsi"
EOF
clang -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
  -I "$CAMERA_TREE/include" "$CAMERA_WORK/dt-test/j715-camera-resources.dts" \
  > "$CAMERA_WORK/dt-test/j715-camera-resources.pp.dts"
"$CAMERA_TREE/scripts/dtc/dtc" -I dts -O dtb \
  -o "$CAMERA_WORK/dt-test/j715-camera-resources.dtb" \
  "$CAMERA_WORK/dt-test/j715-camera-resources.pp.dts"
```

追加ノードは3つとも disabled のまま。これは syntax/resource 試験であり、
有効な camera DT の完成や dtbs_check / 実機動作の証明ではない。この test DTB は実機に配置しない。
preview fragment は `j715-imx958-preview-presets.dtsi`。config 6 / input3040x2880 は実測ログ、
1280x720 の中央1:1 crop は提案値で、macOS 出力 crop の実測値ではない。

## 11. KUnit 実行とテスト環境

C module の compile/link 成功と KUnit 実行成功を混同しない。
旧 release 用に作った .ko を VM の別 kernel へ insmod したり、vermagic を強制無視したりしない。

実行する場合は破棄可能な ARM64 VM の別ブートで、kernel と modules を一致させる。
VM の virtio/block/console 等が使える診断用 config は別に作り、M4 実機用 config を上書きしない。
既存 config が VM 起動に必要な driver を含むとは確認していないため、このブート手順自体は未検証。

診断 kernel には KUNIT=y、VIDEO_APPLE_ISP=m、VIDEO_APPLE_ISP_KUNIT_TEST=y、
APPLE_DART_REMAP_KUNIT_TEST=y、VIDEO_APPLE_ISP_IPC_LAYOUT_KUNIT_TEST=m を設定する。
KUNIT_ALL_TESTS は有効化せず、必要な test だけを選ぶ。release も `-omarchy-m4-camera-kunit` 等に分ける。
診断用 source/config を別ディレクトリで用意する例（この VM ブート自体は未検証）:

```bash
python3 "$CAMERA_PROJECT/tools/prepare-j715-camera.py" "$CAMERA_BASE" "$CAMERA_WORK/kernel-camera-kunit"
cd "$CAMERA_WORK/kernel-camera-kunit"
scripts/config --enable KUNIT --disable KUNIT_ALL_TESTS \
  --module VIDEO_APPLE_ISP --enable VIDEO_APPLE_ISP_KUNIT_TEST \
  --enable APPLE_DART_REMAP_KUNIT_TEST --module VIDEO_APPLE_ISP_IPC_LAYOUT_KUNIT_TEST \
  --set-str LOCALVERSION '-omarchy-m4-camera-kunit'
# VM の virtio / storage / console 等を確認してから olddefconfig とビルドを行う
"${camera_make[@]}" olddefconfig
```

VM 用 kernel と同じ build の modules を VM のみに配置した後の例:

```bash
uname -r
sudo modprobe apple-isp
sudo modprobe isp-ipc-layout-test
sudo dmesg > camera-kunit-dmesg.log
# debugfs が既に使用可能な場合の結果一覧
find /sys/kernel/debug/kunit -name results -type f -print
```

確認する suite は apple-isp 系と apple-dart-static-remap。
DART は builtin の場合 boot 時に結果が出る。KTAP の失敗・skip・kernel warning を分けて報告する。
ここまでの test は fake device / memory-backed MMIO を使う。実機 ISP/DART/LED の動作は保証しない。

## 12. 次の実装作業の順序

1. **VM build と KUnit 実行の不足を埋める**。full build の最初の失敗・config diff・toolchain を残す。
2. **J715 の mailbox/gpio と power/clock を確定する**。macOS driver/loader と実機資料を照合し、
   仮 offset や M5 の値を埋めない。virtual PMGR の zero offset は使わない。
3. **Linux firmware handoff を確定する**。対象 boot の text/data/heap 予約・IOVA・loader 更新の必要性を調べる。
   macOS の物理アドレスを Linux に固定しない。loader flash / EFI/NVRAM 更新は本書で自動実行しない。
4. **module/revision と setfile を確定する**。installer PR #208 の Git ソースを取得・レビューし、
   自分の macOS の appleh16camerad から抽出する。section 0x50f の sensor ID / magic / 長さ等を照合する。
   2224 と2226のどちらかをセンサー型番だけで選ばない。blob/calibration を公開 Git に置かない。
5. **LED を STREAMON/STOP/失敗/halt と結合する**。macOS の観察は記録済みだが Linux で検証が必要。
   `privacy_blocked` を単に false にする、DT の boolean だけで解除する、M5 の GPIO を流用することはしない。
6. **完全な J715 ISP DT と bindings を仕上げる**。disabled DART draft / proposed preview は資料として使い、
   clock/power/firmware/indicator が揃う前に単に status=okay へ変更しない。
7. **実機起動の復旧経路を確認してから実機試験**。通常配布は omarchy-m4-update/channel の規約に従う。
   experimental tar を動作確認済み package として扱わない。

upstream 取得が必要な場合（通常のネットワーク利用可能環境で実行）:

```bash
git clone https://github.com/omacom/omarchy-mac-installer.git installer-review
git -C installer-review fetch origin refs/pull/208/head:refs/remotes/origin/pr-208
git -C installer-review rev-parse origin/pr-208
# 取得 SHA と上記の確認済み SHA が違う場合は差分をレビューする
```

ソースコードのコメント・commit message は英語、調査文書と進捗は日本語。
汎用 ISP/IOMMU と J715 固有の変更を分ける。外部 push / PR 作成は未依頼なので行わない。

## 13. 実機テストの実行条件と順序

実機の既知の正常 kernel/modules/DTB/boot chain を別名・別経路で保持し、復旧の実起動を確認する。
実際の boot file/entry はこの対話で権限不足により確認できていないため、特定の名前を仮定しない。
既定 boot entry 変更は元タスクで明示承認が必要。未承認の変更・firmware flash / NVRAM 更新は行わない。

indicator と firmware/DT の条件が揃い、承認された独立 kernel 起動後に:

```bash
uname -a
sudo dmesg | grep -Ei 'isp|camera|sensor|firmware|dart|iommu|v4l2'
v4l2-ctl --list-devices
# 名前と media topology で内蔵カメラだと確定したノードを明示する
v4l2-ctl -d /dev/CONFIRMED_CAMERA --list-formats-ext
wpctl status
```

capture の具体例と画像検証は `05-testing.md`。実際に列挙された形式・サイズだけを使う。
1フレーム→短い bounded capture→再開閉の順とし、LED と DART fault を同時に確認する。
黒/破損画像、orientation/color、終了時停止・電源停止、アプリ異常終了を検査する。
その後に PipeWire / カメラアプリ / browser を個別にテストする。
GPU/display/audio/入力/SSD の回帰と、可能な状態で suspend/resume も確認する。
既存の sleep 制限がある場合は状態を確認し、camera 試験のために勝手に解除しない。

## 14. 次の担当者が返すもの

`VM-RESULTS-TEMPLATE.md` を記入し、以下を新しい結果ディレクトリにまとめる。

- VM architecture、toolchain 全 version/path、Rust source と libclang の選択。
- base archive/source の同定と camera-preparation.json、config before/after/diff。
- preflight、full build、KUnit の全ログ。失敗した場合は最初の error と前後も残す。
- Image/modules/DTB ができた場合の release、サイズ、SHA256。秘密鍵は含めない。
- 実機試験は「未実施」と「失敗」と「成功」を区別し、Linux LED と macOS 観測を区別する。
- 残る未確定値、次に必要な入力・変更、既存機能の回帰結果。

成功していない機能を WORKING と報告せず、既存環境に導入しない段階でも結果を返す。
