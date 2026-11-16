# J715 のハードウェア識別

状態: **PARTIAL**。macOS の実機 IODeviceTree と IOService を解析し、ISP/DART のリソースを確認した。
追加動作ログからセンサーは **IMX958（sensorID=0x958）** と確認できた。
表示灯は macOS で点灯・消灯したというユーザー観測を得たが、Linux での制御機構は **BLOCKED** のまま。

採取元はユーザーが用意した `/mnt/transfer/j715-camera-inspection/`。
macOS 27.2.1（26B131）、Mac16,13 / J715AP / Apple M4。
raw ファイルと再構成した ADT は Git に含めず、private 作業ディレクトリで解析した。
個体 serial/calibration と、誤って固定値として使われないよう firmware の物理配置は
公開用 `j715-resource-summary.json` から除外した。

| 項目 | 実機採取から確認した値 |
|---|---|
| ISP compatible（Apple ADT） | isp,isp-generic-1 / isp,s5l8960x |
| ISP MMIO | 0x48c000000 / 0x3ff0000 |
| ISP 補助 MMIO | 0x380700000 / 0x18000 |
| ISP IRQ の列 | 369, 370, 371, 372, 382 |
| 撮像センサー | IMX958。追加ログの sensorID とモデル名が一致 |
| ADT sensor-type | 0x18（platform type。センサー型番ではない） |
| DART banks | 0x48e8c0000 / 0x48e8e0000 / 0x48e900000、各 0xc000 |
| DAPF instance 0 | ADT reg[5]、0x48e8d0000 / 0x4000 |
| DART IRQ | 387 |
| ISP mapper stream | 0 と 12 |
| remap source list | 1, 2, 3, 6, 7, 10, 11 |
| VM base / size | 0x10000000000 / 0xe0000000 |
| DAPF windows | 13 範囲。上流 apple_isp_dapf_t8132 の順序・開始・終了と全一致 |
| firmware（IOService） | 6.105、Oct 15 2026 - 20:38:03、FirmwareLoaded=Yes |
| 初回採取時状態 | FrontCameraActive=No / FrontCameraStreaming=No |
| 追加の撮影中 IORegistry | FrontCameraActive=Yes / FrontCameraStreaming=Yes |

ADT の reg は arm-io bus-relative。親 ranges を通した物理アドレスを表に示した。
IOService の IODeviceMemory とも完全一致した。
DART instance の先頭 FourCC は little-endian 数値であり、その後の文字列 label と扱いが異なる。
DAPF record は52 bytes、segment-ranges record は32 bytes（size と flags は各 u32）。
size と flags を u64 として結合してはならない。

firmware segment は __TEXT と __DATA の2件。size はそれぞれ 0xcd0000 と 0xe1c000、
virtual 欄は 0 と 0xcd0000、remap 欄は 0x10000000000 と 0x10000cd0000。
physical 欄は今回の macOS boot に依存する値なので Linux DT へ固定しない。
Linux boot で予約・引渡しされる text/data/heap を別途確認する必要がある。

PMGR の実レジスターは ISPSENS0=0x188、ISPSENS1=0x190、ISP_SYS=0x530（各 pmgr reg[0] 内）。
ISP_CPU/FE/BE/SECURE 等は ADT 上 virtual。virtual の zero offset を実レジスターと誤認しない。
ISP_SYS の親 AFISOCNI4 も virtual であり、完全な Linux power-domain 構成は未確定。
clock IDs は 0x180/0x182 だが、rate と起動順の実装は未確定。

確認できなかったもの:

- module/build revision と適合 setfile。センサー型番だけで 2224_01 / 2226_02 を決定しない。
- ISP register block 内の mailbox/gpio 分割。M5 の +0x2924000 等は流用しない。
- Linux boot での firmware handoff と heap 範囲。
- camera-active indicator。EIC ノードや cil-gpio プロパティが見つからないことは、
  hardware LED である証拠にはならない。

IOService の AppleH16CamIn と appleh16camerad の存在は確認できたが、
初回採取は非撮影状態で、公開プロパティに sensor/module ID はなかった。
[追加動作ログ](06-macos-camera-logs.md)で sensorID=0x958 と IMX958 の独立した記載が一致した。
macOS は config 6、raw 3040x5760 / processed region 3040x2880 を使用し、fps=30 を要求している。
30fps は測定 frame rate ではない。streaming state は 1 → 0、撮影中 snapshot も Streaming=Yes。
元ログの参照箇所は sensorID が283行、IMX958 が304行、pipeline shape が274行、state 変化が311/514行。
per-module serial や元ログ全文は Git に追加しない。

ユーザー観測: カメラセンサーエリアの LED が使用中に点灯し、使用後に消灯した。
macOS の indication は観測できたが、hardware interlock か firmware/software 制御かは未確定。
この観測だけでは Linux の privacy_blocked を解除しない。

再現:

```sh
python3 tools/ioreg-adt.py /path/to/iodevicetree.txt /tmp/j715-camera.adt
python3 tools/camera-m4-hardware.py /tmp/j715-camera.adt \
  --ioservice /path/to/ioservice.txt \
  --driver /path/to/patched-kernel/drivers/media/platform/apple/isp/isp-drv.c \
  --dart-driver /path/to/kernel/drivers/iommu/apple-dart.c \
  --camera-log /path/to/appleh16camerad-live.log \
  --active-registry /path/to/AppleH16CamIn-active.txt
```

再構成 ADT は原本 binary ADT と同等とは限らない。tools/ioreg-adt.py の制約も参照する。
新ツールは J715/Mac16,13/target-type の一致を要求し、serial/calibration を出力しない。
firmware/setfile の抽出登録は sensor/module/revision を確認してから行う。
proprietary blob と per-module calibration は再配布しない。
