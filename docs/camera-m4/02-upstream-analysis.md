# 上流 ISP 変更の分析

状態: **PARTIAL**。PR #421/#422 の固定 Git オブジェクトを取得済み。
ISP ソース差分・依存・M5 固有 DT と表示灯処理を確認し、#421 の ISP 部分を 7.1.9 向けに移植した。
フルカーネルと実機動作の検証は未完了。

| 参照 | 固定 SHA |
|---|---|
| clone の integration/aurora | 39d5f88ab4e54bb61eecd3fba79e3242005f2f76 |
| PR #421 head | af2676a9ee596bc94bb016d52a925ce550c46963 |
| PR #422 head | 8916070002f4dc60e1bca6995b9c52fa0131683f |
| integration と #421 の merge-base | 8eddf5aeb6acfb07ec3ca7bdcb62170685493b28 |

integration と merge-base の ISP ディレクトリに差分がないことを確認した。
#421 の変更は ISP 以外に J616 系の DT preset と開発資料を含むが、これらは J715 移植へ取り込まない。
#422 の追加は ISP のほか NVMe/SART/RTKit/PMGR など T6050 固有のシステム対応を含む。
T8132 のモジュールビルドに #422 のコードは不要であった。

| Component | Existing support | Missing changes / 今回の処置 | Source commit |
|---|---|---|---|
| ISP core | ローカル 7.1.9 旧 ISP | H17/T8140 前提 snapshot を patch 0001 として保存 | 39d5f88ab4e54bb61eecd3fba79e3242005f2f76 |
| T8132 | 稼働 module に match なし | patch 0002 に追加、ビルド確認 | 5f3511a0e7e93395a83273946947e84cb93bf593 |
| DART | T8132 driver と T8110 fallback は存在 | ISP 側にフィルター設定・readback。ISP DART の DT は未実装 | 00e88f127ec23bee3605e54c7bd9338ff022980f |
| 起動遅延 | 旧 ISP にはない | T8132 の検出・起動を stream 開始まで遅延 | 05d1fb1164e7888ed348881b9be77c592f928518 |
| firmware data | 復元なし | data reserved-memory の保存・復元 | d048a44f98da8d2b452d81c8412ea292aa0a6209 |
| 電源停止 | T8132 非対応 | WFI/quiesce を伴う停止と再開 | 9e0ff10bec022b5ef8c505b9535632e6a12504e9 / a17e540a0df57cb4b304b15212a5f3eb5de45037 |
| DMA/IOVA | drm_mm ベース | maple tree で IOVA 範囲を管理、IPC/buffer lease 修正を含む | d9a5c3bb53e806776f1874ed2676d2d2ee811a9f |
| Camera sensor | J715 型番不明 | firmware の channel-info による検出経路はあるが実機未実行 | 未確定 |
| Firmware | bootloader が実体を準備する設計 | text/data/heap の J715 実値・setfile は未確定 | 未確定 |
| Device Tree | J715 DTS に ISP なし | J715 の ADT が必要。M5 の固定値は流用しない | 未実装 |
| V4L2 | 旧 module 有効、device なし | 連続 single-planar capture、NV12/P010 等を移植、実機未検証 | 7a32d672dfc9291a2d17994fd4f686b819da38b8 |
| Privacy | J715 indicator 不明 | downstream patch 0003 で J715 STREAMON を拒否 | この作業の独立パッチ |

T8132 は H17 ABI を match data で選ぶ。旧世代向け version enum は 12.3/12.4/13.5/14.7。
H17 はこの version enum による判定を行わない。これは全 firmware 版の動作保証ではない。
J715 の firmware 版は依然未確認。

T8132 は T6040 系の coprocessor と scaler 1 経路を使う。
T6040 の 4 AMCC/8 slot に対して T8132 は 2 AMCC/2 window。
PMP scratch 値が未確定なので T8132 では PMP_CTRL_SET を送らない。
T8132 の MMIO/DAPF テーブルの一次根拠は upstream コメントでは **J713 ADT** と明記されている。
同じ SoC 向け上流コードとして移植したが、J715 での一致を証明したわけではない。
T8142 は T8140 系の IOVA mask/mailbox routing を使い、T8132 の restore/quiesce/deferred-start とは異なる。
T6050 の watchdog/light GPIO・firmware 物理配置は #422 の J714c 固有情報であり移植していない。

DAPF は最初の iommus の DART から reg-names=dapf を探し、T8110-compatible と領域サイズを検証する。
フィルター各 window を電源投入後に書き、readback に失敗すると起動を失敗させる。
firmware が参照する MMIO は必要な範囲を identity-map する。
フィルター無効化、広範な代替 map、IOMMU bypass は追加していない。

Kconfig の APPLE_PMP_REPORT は既存 7.1.9 の drivers/pmdomain/apple に定義済み。
今回の ISP ソースは新しい pmp-report.h API を呼ばず、新たな PMP ドライバー移植は不要。
maple tree・reserved-memory API を含むコンパイルと modpost は通過した。
ただし clock/reset/power-domain と bootloader の firmware handoff は J715 実機の未解決事項。

#422 の camera-light 処理（5a3e9d8a5f0b2e64cf89b4a96bb6f158afa50df7、
04606609e94c7af8daa464048388a4cd8f9e0af4）を確認した。
J714c の専用 GPIO 設定・点灯 readback、点灯中のみ watchdog を feed、halt 時の消灯を含む。
これを J715 の表示灯機構の根拠にはできない。

[installer PR #208](https://github.com/omacom/omarchy-mac-installer/pull/208) の
cffff8b5ed2cbaa8dd52233188251e9d3791ef85 は Web 上で確認した IMX958 抽出変更。
同 installer の Git オブジェクトは今回の取得対象に含まれていないため、全 extractor ソースのレビューは未完了。
センサー未確定の J715 用抽出登録は追加していない。

今回再利用した ISP 履歴（上流の author と signoff は patches-kernel/j715-camera/upstream-history.txt）:

```text
a42c128a86c0710806b203c5f78cb7e030565343 media: apple: isp: Zero the lens shading strides of H17 setfiles
a7ed025103dadb01d8bc6998dad9662e8959be58 media: apple: isp: Add T6040 support
de5f82a04fd793eab583511c8e28840dca272ffd media: apple: isp: Keep T8140 off the T6040 setfile and main memory paths
74e7d2bb38f8dd0cad140624812d849e083ed53f media: apple: isp: add IMX958 P010 preview and config discovery
2a5ef7da4b7e9eb7f2fc3ad1cb84173e6026de32 media: apple: isp: reject P010 command ACKs after the deadline
b072f206dfc65b2de8d9558d959ba0c3c46de73d media: apple: isp: requeue the last IMX958 NV12 buffer immediately
800aa7f358f5930f040a1f0aa55d779dd52ddd1c media: apple: isp: accept full-width P010 completion address pairs
b0ca3cee54afa08ba8f2d40df717e696fcfddd4b media: apple: isp: remove parameter-controlled format exposure
3d3d6ff59056fc61844ef58531d2ad4bffa3de4c media: apple: isp: copy complete IPC messages with FORTIFY enabled
7a32d672dfc9291a2d17994fd4f686b819da38b8 media: apple: isp: use the contiguous single-planar capture API
b435c6c60110a114b7097877aacf35d598c537f1 media: apple: isp: let a P010 queue allocate its two buffers
86092424459bfd6d417a1f69372c01e23e38c5d3 media: apple: isp: report and propagate sensor tuning failures
338bff6ddf238b266ff2dd4f68240610615e9697 media: apple: isp: account for NV12 flicker replies in tuning tests
1e7c5daa7e3220549955c0659c7bf8e4d86a9157 media: apple: isp: report the frame gain and exposure
91a1c6487df8af081dd067b0840e7f4b1e66f81e media: apple-isp: derive call sizes from processed crop extents
d9a5c3bb53e806776f1874ed2676d2d2ee811a9f media: apple: isp: allocate IOVA ranges without drm_mm
fb310d822f4204746f57fffbde81e528c32efb78 media: apple: isp: recover from a timed-out P010 command
e0b635eef977de6ae57cd4d6a51d87f1801fe0a3 media: apple: isp: set up the temporal filter per sensor as macOS does
14bfc0869cf4c4ca6755ab0c56e72c2ac05af58a media: apple: isp: tell auto exposure the mains frequency
00e88f127ec23bee3605e54c7bd9338ff022980f media: apple: isp: Program the DART address filter
05d1fb1164e7888ed348881b9be77c592f928518 media: apple: isp: Let resident firmware start at the first stream
5f3511a0e7e93395a83273946947e84cb93bf593 media: apple: isp: Add T8132 support
d048a44f98da8d2b452d81c8412ea292aa0a6209 media: apple: isp: Optionally restore the firmware data before each start
9e0ff10bec022b5ef8c505b9535632e6a12504e9 media: apple: isp: Power restartable firmware down completely
a17e540a0df57cb4b304b15212a5f3eb5de45037 media: apple: isp: Power the T8132 ISP down between streams
58900fd9293b2d1e256b7e7c62792a12c47b8b65 media: apple: isp: Add T8142 (M5)
af2676a9ee596bc94bb016d52a925ce550c46963 arm64: dts: apple: t604x-j614-j616: scale the 720p camera preset
```

出所: [PR #421](https://github.com/omacom/linux-aurora/pull/421)、
[PR #422](https://github.com/omacom/linux-aurora/pull/422)。
集約差分なので単一 commit の cherry-pick ではない。各ファイルの hash と PR head を manifest に固定した。
