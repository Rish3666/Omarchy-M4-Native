# M4 MacBook Air 15-inch（J715）カメラ開発

現在: **PARTIAL / BLOCKED**。上流 #421 の T8132 ISP 対応を移植し、7.1.9 向けの
通常・KUnit 込み module build に成功した。実機初期化・フレーム取得は未達成。
J715 の ISP/DART 実値と IMX958 センサーは確認できたが、setfile revision/firmware handoff/Linux indicator が未確定なので、専用ガードで撮影を拒否する。
既存カーネル・起動環境は変更していない。

- [環境](01-environment.md)
- [上流分析と実コミット](02-upstream-analysis.md)
- [ハードウェア識別・macOS 採取](03-hardware-identification.md)
- [実装・ビルド・ロールバック](04-implementation.md)
- [実際の検証結果・実機試験手順](05-testing.md)

| マイルストーン | 状態 |
|---|---|
| A: Hardware identified | PARTIAL: J715/T8132・ISP/DART・IMX958 確認、setfile/indicator/firmware handoff 未確認 |
| B: Driver implemented | IMPLEMENTED / UNTESTED: T8132 module compile 済み、実機未初期化 |
| C: Camera capture | BLOCKED: ISP DT なし、Linux indicator 未検証、撮影をコードで拒否 |
| D: Desktop integration | BLOCKED: フル kernel build は VM で未検証。対話環境側は Rust 依存不足。PipeWire/browser 未検証 |

追加コードは 5 本の kernel patch、hash 検証付き準備・採取・独立ビルドツール、回帰テスト。
`patches-kernel/j715-camera/series` と manifest に適用順・出所を固定した。
実機に基づく DART DT 草案は全ノード disabled のまま追加した。仮 MMIO/IRQ や M5 用 firmware 固定値は追加していない。

ユーザーのビルド環境は aarch64 Arch Linux（Omarchy）VM / Clang21.1.8 / Rust1.93.1 と確認済み。
次に必要なのは (1) この VM での依存確認と full build/KUnit 実行、(2) setfile module/revision と Linux firmware handoff/indicator の実装根拠、(3) 権限のある実機ログ閲覧環境。
表示灯の制御実装と点灯・消灯の実機確認後に、撮影拒否ガードを正しい indicator 連動処理へ置き換える。
その後、独立 kernel の起動、V4L2 capture、PipeWire/browser、suspend/resume と既存機能の回帰を検証する。

採取済みの IORegistry から ISP/DART を解析するツールと、serial/calibration を除いた
[j715-resource-summary.json](j715-resource-summary.json) を追加した。
初回の採取手順にカメラ動作ログが不足していたため、追加手順を独立文書にまとめた。

追加ログから IMX958 / config 6 を確認した。ユーザーは macOS でセンサーエリア LED の
使用中点灯・終了後消灯を観測した。Linux 側は未検証なので撮影ガードは維持している。
DART の static remap backport と、J715 入力 geometry に基づく実験 preview preset を追加し、
モジュール・DT 構文を確認した。KUnit 実行と Linux 実撮影は未達成。

引継ぎ先は [ビルド・試験指示書](07-handoff-instructions-ja.md) を入口にする。
[同梱物・Transfer コピー結果](08-handoff-package.md) に実際の保存先と制約を記載した。
