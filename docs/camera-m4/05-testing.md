# 検証記録と次の実機試験

2026-11-16。T8132 対応のコンパイルは確認したが、camera capture の成功報告ではない。

| 検証 | 結果 |
|---|---|
| 実機識別 | WORKING: J715/T8132 を読み取り確認 |
| Python 回帰テスト | 16 件成功。private data 除外、ADT identity、既存出力の保護、改変 base 拒否など |
| 準備ツール | 4 パッチの適用と最終 hash 照合成功。独立した完全 kernel コピーを作成 |
| 上流取得 | #421/#422 は通常端末で fetch 済み、固定 SHA のソースを解析 |
| #421 ISP の通常 module build | 成功（7.1.9 の既存ヘッダー・media 依存を使用） |
| J715 guard + IPC 修正込み通常 module build | 成功、FORTIFY 警告を解消 |
| KUnit ケース込み module build | 成功。上流テストと追加した privacy/IPC テストをコンパイル・link |
| KUnit 実行 | 未実施。モジュールをロードしていない |
| フル kernel Image/modules/DTB/package | この対話環境は Rust 依存不足で未実施。ユーザー VM での full build は未検証 |
| V4L2 デバイス・フレーム | BLOCKED: ISP DT なし、表示灯未確認、撮影ガードあり |
| PipeWire/browser | 未検証。sandbox からは PipeWire に接続できない |
| indicator | 機構・点灯/消灯未検証。STREAMON 拒否ガードのみ実装 |
| suspend/resume・GPU/音声回帰 | 未実施 |

テストコマンド:

```sh
python3 -m unittest discover -s tests -p 'test*camera*.py' -v
bash -n tools/camera-m4-fetch.sh tools/build-j715-camera.sh
git diff --check
python3 tools/prepare-j715-camera.py ~/j715/kbuild /path/to/new-camera-source
```

準備の実行済み出力: `~/Work/camera-build/t8132-kernel-final`。
元の kbuild は変更していない。出力は -omarchy-m4-camera-test を config に設定済み。

ビルド検証は元 kbuild を `~/Work/camera-build/baseline` に複製してから実施。
M= で独立した外部モジュール出力を使い、mc/v4l2-core/videobuf2/ISP をまとめて link した。
KUnit 込みでは lib/kunit も含めた。CONFIG_VIDEOBUF2_DVB=n は無関係な DVB bridge を対象から外す
この module-only 検証用の指定であり、実験 kernel の保存 config は変更していない。

```sh
# 下の M ディレクトリには必要な依存ソースと更新済み ISP を配置済み
make -C ~/Work/camera-build/baseline ARCH=arm64 LLVM=1 W=1 -j8 CONFIG_VIDEOBUF2_DVB=n M=~/Work/camera-build/pr421 modules
# KUnit を含めた比較検証（実行はしない）
make -C ~/Work/camera-build/baseline ARCH=arm64 LLVM=1 W=1 -j8 CONFIG_VIDEOBUF2_DVB=n KCFLAGS=-DCONFIG_VIDEO_APPLE_ISP_KUNIT_TEST=1 M=~/Work/camera-build/pr421 modules
```

最終ログは `~/Work/camera-build/t8132-final-build.log` と
`~/Work/camera-build/t8132-final-kunit-build.log`。
以前の単独 ISP/全 media/KUnit 依存なしの試行は、それぞれ未解決外部シンボルで失敗したが、
必要な依存を同時ビルドした最終試行は modpost を含め成功した。
元カーネルの Clang 21.1.8 と実行中の 23.1.4 の差異警告は残る。
IPC payload copy の FORTIFY 警告は patch 0004 で解消し、最終ログに source 警告はない。

これらの .ko は旧 kernel の header/Module.symvers へのコンパイル互換性検証用であり、
実験 kernel 一式の代わりにインストールしてはならない。既存 module の上書きやロードはしていない。

実験ツリーの `make ARCH=arm64 LLVM=1 rustavailable` は bindgen 不在で失敗した。
ログは `~/Work/camera-build/t8132-rust-preflight.log`（同じ ISP で IPC 警告修正前の
隔離ツリーに対する toolchain 検査）。Rust を無効化して GPU なしの Image を作る代替は行わない。
互換ツールチェーンが揃った後に、フルビルドと config の Rust/GPU/audio 維持を検証する必要がある。

次の実機試験は、J715 の全リソース・firmware・indicator を検証し、
独立カーネルのビルドと復旧起動を確認してから行う。

```sh
# 権限のある実機端末でログを採取
sudo dmesg | grep -Ei 'isp|camera|sensor|firmware|dart|iommu|v4l2'
v4l2-ctl --list-devices
# 内蔵カメラであると照合したノードを明示する
v4l2-ctl -d /dev/CONFIRMED_CAMERA --list-formats-ext
wpctl status
```

表示灯の連動を確認できる監視下で、列挙された形式・解像度を選択して試験する。
NV12 対応が確認できた場合の例:

```sh
v4l2-ctl -d /dev/CONFIRMED_CAMERA --set-fmt-video=width=1280,height=720,pixelformat=NV12 --stream-mmap --stream-count=30 --stream-to=/tmp/j715-camera.nv12
ffmpeg -f rawvideo -pixel_format nv12 -video_size 1280x720 -i /tmp/j715-camera.nv12 -frames:v 1 /tmp/j715-camera.png
```

ファイルサイズだけで成功とせず画像を観察する。orientation、黒画像、色、露出、frame count、
DART fault の不在を確認し、再開閉・中断・異常終了・suspend/resume・電源停止を試す。
LED は open 時だけでなく STREAMON/STREAMOFF と連動することを確認する。
最後に PipeWire、アプリ、ブラウザーを個別検証する。

macOS 採取後の追加検証:

- J715 の translated ISP MMIO は IOService の IODeviceMemory と一致。
- ADT の DAPF 13 範囲は上流 T8132 テーブルと全一致。
- Python テスト16件成功（address translation、FourCC、segment/DAPF 長検査、private data 除外を追加）。
- DART resource 草案を J715 DTS と一緒に cpp/dtc でコンパイル成功。
  base/candidate を比較して既存ノードの全 property 不変と、追加3ノードが disabled であることを確認。
  各 reg/IRQ/remap/DAPF は採取値と照合した。
- 比較用 DTB とログは `~/Work/camera-build/macos-derived/`。
  /boot への配置、実機への適用、再起動、撮影は行っていない。

草案の構文チェックは dtbs_check や実機動作の証明ではない。
旧 DART backend の remap 処理不足と、virtual power state/firmware handoff/indicator が残るため
フル初期化・撮影は引き続き未検証。

今回の環境での草案コンパイル再現例（出力は /tmp のみ）:

```sh
cat > /tmp/j715-camera-resource-check.dts <<'EOF'
#include "~/j715/kbuild/arch/arm64/boot/dts/apple/t8132-j715.dts"
#include "~/Work/Omarchy-M4-Native/dts/camera-m4/t8132-j715-dart-resources.dtsi"
EOF
clang -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
  -I ~/j715/kbuild/include /tmp/j715-camera-resource-check.dts \
  > /tmp/j715-camera-resource-check.pp.dts
~/j715/kbuild/scripts/dtc/dtc -I dts -O dtb \
  -o /tmp/j715-camera-resource-check.dtb /tmp/j715-camera-resource-check.pp.dts
```

追加で既存 IORegistry converter のテスト8件も成功した。
DTB 比較では boot CPU と reservation map も不変であることを確認した。

追加動作ログ・表示灯観測後:

- IMX958 を sensorID=0x958 とモデル名の両方で確認し、typed summary へ反映した。
- macOS の Streaming=Yes snapshot と、ログの Streaming 1 → 0 を確認した。
- ユーザーはセンサーエリア LED の使用中点灯・終了後消灯を観測。Linux indicator の検証とは区別する。
- DART patch 0005 の normal/KUnit 込み module build は W=1 で成功。
  ログは `~/Work/camera-build/dart-remap-build.log` と `dart-remap-kunit-build.log`。
  warning は既存 kernel Clang 21.1.8 と現在の 23.1.4 の差異のみ。KUnit は未実行。
- 5パッチの準備済み tree の全最終 hash を manifest と照合した。
- IMX958 preview fragment の test wrapper を cpp/dtc でコンパイルした。
  config/input は実ログと一致し、提案 crop が入力内・中央・1:1 であることを検査した。
  wrapper の ISP node は disabled。Linux frame 取得はしていない。
- 現在の Python 回帰テストは16件通過。

DART compile の再現は、隔離ディレクトリに更新した apple-dart.c / test.c を配置し、
Makefile に `obj-m += apple-dart.o` と `ccflags-y += -I$(srctree)/drivers/iommu` を指定して行った。
normal は `make -C .../baseline ARCH=arm64 LLVM=1 W=1 -j8 M=.../dart-remap modules`。
KUnit 込みは `KCFLAGS=-DCONFIG_APPLE_DART_REMAP_KUNIT_TEST=1` と、先にビルドした
lib/kunit の exports を含む `KBUILD_EXTRA_SYMBOLS=.../pr421/Module.symvers` を指定した。
これらは compatibility 検証用の外部 module で、実機の既存 .ko を置換してはならない。

Rust 依存の追加確認では標準 core source も不在だった。scripts/rust_is_available.sh は
bindgen 検査後にこの source の存在も要求するので、Rust compiler に対応した rust-src も必要。
元 build の Clang 21.1.8 / Rust 1.93.1 と現在の 23.1.4 / 1.99.1 の互換性は未検証。
現在稼働 DT に apple,remap-streams はないことを確認したが、backport の実機回帰の代わりにはならない。

VM 引継ぎ時の補足: aarch64 Arch / Clang21.1.8 / Rust1.93.1 はユーザー確認済み。
この環境での full camera kernel / KUnit 実行は次担当の検証事項。
新規 preflight はこの対話環境で compiler/version・bindgen/source 不足を FAIL として検出した。
これは VM の失敗結果ではない。既存元 kernel source を変更せず fallback archive を作成し、
pinned ISP/DART の base hash を照合した。通常 mrproper の失敗と clean-dirs= でのコピー内清掃を記録した。
