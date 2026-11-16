# 検証記録と次の実機試験

2026-11-16。この記録は camera bring-up の成功報告ではない。

| 検証 | 結果 |
|---|---|
| 実機 model/compatible | WORKING: J715/T8132 の読み取り確認 |
| 採取ツール | Linux 実機で JSON 生成済み、ADT は合成データ試験のみ |
| 単体テスト | 3 件成功 |
| shell 構文・diff 空白 | 通過 |
| 上流取得 | PARTIAL: 通常端末で clone 成功、この実行環境での PR fetch は名前解決失敗 |
| ISP 旧ソースの W=1 コンパイル | 各 C オブジェクトと apple-isp.o の生成を確認、警告あり |
| 単独 ISP モジュールの link | media/vb2/V4L2 の未解決シンボルで modpost 失敗 |
| 旧 ISP + 必要な media 依存モジュールの link | 成功（T8132 対応を含まない、未ロード） |
| T8132 ドライバー/フル kernel build | BLOCKED: 上流未取得・移植未完了 |
| 実験用 tar/起動 | 未実施 |
| V4L2 デバイス・フレーム | BLOCKED: ノードなし |
| PipeWire/browser | BLOCKED: カメラなし、sandbox からセッションバスへ接続不可 |
| indicator | BLOCKED: 制御方式・実動作未確認 |
| suspend/resume、GPU/音声回帰 | 未実施 |

実行コマンド:

```sh
python3 -m unittest discover -s tests -p 'test_camera_m4_inspect.py' -v
bash -n tools/camera-m4-fetch.sh tools/build-j715-camera.sh
git diff --check
python3 tools/camera-m4-inspect.py > /tmp/j715-camera.json
```

既存ツリーを `/home/kazu/Work/camera-build/baseline` に複製してから、
`make ARCH=arm64 LLVM=1 W=1 -j4 M=drivers/media/platform/apple/isp modules` を実行。
元の clang 21.1.8 と現在の 23.1.4 の差異警告、および isp-ipc.c の fortify 警告を確認した。
このビルドは **旧ドライバーの比較用** であり、T8132 対応の証拠ではない。
ログは `/home/kazu/Work/camera-build/baseline-isp-build.log`。
`M=drivers/media` 全体では I2C ATR/mux など他ドライバーの外部依存により modpost が失敗した。
そこで必要な範囲をまとめ、不要な DVB ブリッジを外して再検証した。最終コマンドは成功し、
`apple-isp.ko`（142912 bytes）と media/vb2/V4L2 モジュールを生成した。
インストール・ロードはしていない。最終ログは
`/home/kazu/Work/camera-build/baseline-subset-final.log`。

比較用ビルドの再現（元ツリーのコピーと、まだ存在しない出力ディレクトリで実施）:

```sh
cp -a --reflink=auto /home/kazu/j715/kbuild /tmp/j715-camera-baseline
mkdir /tmp/j715-camera-media
ln -s /tmp/j715-camera-baseline/drivers/media/mc /tmp/j715-camera-media/mc
ln -s /tmp/j715-camera-baseline/drivers/media/v4l2-core /tmp/j715-camera-media/v4l2-core
ln -s /tmp/j715-camera-baseline/drivers/media/common/videobuf2 /tmp/j715-camera-media/videobuf2
ln -s /tmp/j715-camera-baseline/drivers/media/platform/apple/isp /tmp/j715-camera-media/isp
printf 'obj-m += mc/ v4l2-core/ videobuf2/ isp/\n' > /tmp/j715-camera-media/Makefile
make -C /tmp/j715-camera-baseline ARCH=arm64 LLVM=1 W=1 -j8 CONFIG_VIDEOBUF2_DVB=n M=/tmp/j715-camera-media modules
```

実験ビルドツールを現行の非 Git kbuild に対して実行すると、Git provenance 検証で停止した。
その時点で出力先は未作成。現状を T8132 対応成果物として梱包しないことを確認した。

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

clone 後の追加検証: upstream `39d5f88ab4e54bb61eecd3fba79e3242005f2f76` の
ISP ディレクトリを `/home/kazu/Work/camera-build/aurora-prereq/isp` にコピー。
上記比較ビルドと同じ mc/v4l2-core/videobuf2 の依存構成で、
`M=/home/kazu/Work/camera-build/aurora-prereq` としてビルド成功。
ログは `/home/kazu/Work/camera-build/aurora-prereq-build.log`。
T8132 未対応の汎用 H17 前提パッチについてのコンパイル確認であり、実機 capture の証拠ではない。
