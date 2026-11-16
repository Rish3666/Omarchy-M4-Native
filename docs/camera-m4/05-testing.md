# 検証記録と次の実機試験

2026-11-16。T8132 対応のコンパイルは確認したが、camera capture の成功報告ではない。

| 検証 | 結果 |
|---|---|
| 実機識別 | WORKING: J715/T8132 を読み取り確認 |
| Python 回帰テスト | 6 件成功。private data 除外、ADT identity、既存出力の保護、改変 base 拒否など |
| 準備ツール | 4 パッチの適用と最終 hash 照合成功。独立した完全 kernel コピーを作成 |
| 上流取得 | #421/#422 は通常端末で fetch 済み、固定 SHA のソースを解析 |
| #421 ISP の通常 module build | 成功（7.1.9 の既存ヘッダー・media 依存を使用） |
| J715 guard + IPC 修正込み通常 module build | 成功、FORTIFY 警告を解消 |
| KUnit ケース込み module build | 成功。上流テストと追加した privacy/IPC テストをコンパイル・link |
| KUnit 実行 | 未実施。モジュールをロードしていない |
| フル kernel Image/modules/DTB/package | BLOCKED: bindgen 不足で Rust 事前検査失敗 |
| V4L2 デバイス・フレーム | BLOCKED: ISP DT なし、表示灯未確認、撮影ガードあり |
| PipeWire/browser | 未検証。sandbox からは PipeWire に接続できない |
| indicator | 機構・点灯/消灯未検証。STREAMON 拒否ガードのみ実装 |
| suspend/resume・GPU/音声回帰 | 未実施 |

テストコマンド:

```sh
python3 -m unittest discover -s tests -p 'test*camera*.py' -v
bash -n tools/camera-m4-fetch.sh tools/build-j715-camera.sh
git diff --check
python3 tools/prepare-j715-camera.py /home/kazu/j715/kbuild /path/to/new-camera-source
```

準備の実行済み出力: `/home/kazu/Work/camera-build/t8132-kernel-final`。
元の kbuild は変更していない。出力は -omarchy-m4-camera-test を config に設定済み。

ビルド検証は元 kbuild を `/home/kazu/Work/camera-build/baseline` に複製してから実施。
M= で独立した外部モジュール出力を使い、mc/v4l2-core/videobuf2/ISP をまとめて link した。
KUnit 込みでは lib/kunit も含めた。CONFIG_VIDEOBUF2_DVB=n は無関係な DVB bridge を対象から外す
この module-only 検証用の指定であり、実験 kernel の保存 config は変更していない。

```sh
# 下の M ディレクトリには必要な依存ソースと更新済み ISP を配置済み
make -C /home/kazu/Work/camera-build/baseline ARCH=arm64 LLVM=1 W=1 -j8 CONFIG_VIDEOBUF2_DVB=n M=/home/kazu/Work/camera-build/pr421 modules
# KUnit を含めた比較検証（実行はしない）
make -C /home/kazu/Work/camera-build/baseline ARCH=arm64 LLVM=1 W=1 -j8 CONFIG_VIDEOBUF2_DVB=n KCFLAGS=-DCONFIG_VIDEO_APPLE_ISP_KUNIT_TEST=1 M=/home/kazu/Work/camera-build/pr421 modules
```

最終ログは `/home/kazu/Work/camera-build/t8132-final-build.log` と
`/home/kazu/Work/camera-build/t8132-final-kunit-build.log`。
以前の単独 ISP/全 media/KUnit 依存なしの試行は、それぞれ未解決外部シンボルで失敗したが、
必要な依存を同時ビルドした最終試行は modpost を含め成功した。
元カーネルの Clang 21.1.8 と実行中の 23.1.4 の差異警告は残る。
IPC payload copy の FORTIFY 警告は patch 0004 で解消し、最終ログに source 警告はない。

これらの .ko は旧 kernel の header/Module.symvers へのコンパイル互換性検証用であり、
実験 kernel 一式の代わりにインストールしてはならない。既存 module の上書きやロードはしていない。

実験ツリーの `make ARCH=arm64 LLVM=1 rustavailable` は bindgen 不在で失敗した。
ログは `/home/kazu/Work/camera-build/t8132-rust-preflight.log`（同じ ISP で IPC 警告修正前の
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
