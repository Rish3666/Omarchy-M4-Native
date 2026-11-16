# J715 のハードウェア識別

状態: **BLOCKED**（センサー・表示灯・ISP リソース未確定）。

確定: この実機は J715/T8132。稼働 Linux DT に ISP ノードがなく、
既存 ISP モジュールに T8132 match もない。

仮説: 上流 T8132 対応が J715 にも移植できる可能性はある。
同一 SoC の J713 情報は比較資料にとどめる。
既存 `docs/t8132-adt-audit.md` は **J713** の履歴であり、そこに記載された
DART アドレスを J715 の確定値として採用しない。

未確定: センサー/module/build revision、ISP MMIO/IRQ、DART の各 stream と filter、
power domain、clock、reset、firmware text/data/heap の予約範囲、indicator/EIC。
IMX958 とも IMX558 とも断定しない。既存ファイル名から実機センサーを逆算しない。

macOS での読み取り専用採取（通常起動、NVRAM/firmware の書換え不要）:

```sh
mkdir -p ~/Desktop/j715-camera-inspection
cd ~/Desktop/j715-camera-inspection
sw_vers > macos-version.txt
system_profiler SPHardwareDataType SPCameraDataType > system-profiler.txt
ioreg -p IODeviceTree -l -w0 > iodevicetree.txt
ioreg -p IOService -l -w0 > ioservice.txt
```

これらの原本にはシリアル番号や calibration が含まれる可能性がある。公開しない。
`SPCameraDataType` の商品名だけではセンサー型番を確定できない。
Linux の作業ディレクトリへ自分で持ち帰った後:

```sh
python3 tools/ioreg-adt.py /path/to/iodevicetree.txt /tmp/j715-camera.adt
python3 tools/camera-m4-inspect.py --adt /tmp/j715-camera.adt > /tmp/j715-camera-resources.json
```

再構成 ADT は原本の binary ADT と同等とは限らない（tools/ioreg-adt.py の説明参照）。
新ツールは許可リストのリソースだけを hex 出力する。Linux DT は big-endian、ADT は
little-endian であり、同じ hex 表現でも解釈を混同しない。
センサーの configuration/calibration blob は自動公開しない。
firmware ログ・channel-info が必要な場合は非公開の手元で確認し、識別 ID のみを記録する。

表示灯は **BLOCKED**。物理 LED 連動かソフト制御か未確定。
EIC がある場合には watchdog と GPIO だけでなく、アクセス制御を含めて確認する。
点灯の観測と、start 成功/失敗・stop・異常終了での連動を実機で確認するまで
通常ストリーミングを有効にしない。

firmware/setfile の導入は、確認済み sensor/module/revision とドライバーの要求パスを照合し、
installer の抽出テストへ該当 entry を追加してから行う。
自分の macOS から抽出した blob の hash/長さ/magic を手元で検証する。
未確認の J715 用 entry や固定オフセットは作成していない。
再配布権を確認できない proprietary blob・calibration はリポジトリにも成果物にも含めない。

PR #421 取得後の補足: T8132 の SoC パラメーターは移植済みだが、upstream の
MMIO/DAPF 根拠は J713 ADT。J715 の実機値が確定したことにはならない。
採取ツールは ADT root の model/compatible/target-type/board-id/chip-id も hex で記録し、
別モデルの ADT を誤用しないための照合材料を提供する。
`segment-ranges` は起動時の firmware 配置であり、M5 の数値を埋め込まず J715 の採取値を使う。
新ガードは J715 の STREAMON を -EACCES で拒否する。表示灯機能を提供するものではない。
