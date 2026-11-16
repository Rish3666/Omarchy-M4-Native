# M4 MacBook Air 15-inch（J715）カメラ開発

現在: **PARTIAL / BLOCKED**。上流 #421 の T8132 ISP 対応を移植し、7.1.9 向けの
通常・KUnit 込み module build に成功した。実機初期化・フレーム取得は未達成。
J715 の ISP/DART 実値は確認できたが、sensor/firmware handoff/indicator が未確定なので、専用ガードで撮影を拒否する。
既存カーネル・起動環境は変更していない。

- [環境](01-environment.md)
- [上流分析と実コミット](02-upstream-analysis.md)
- [ハードウェア識別・macOS 採取](03-hardware-identification.md)
- [実装・ビルド・ロールバック](04-implementation.md)
- [実際の検証結果・実機試験手順](05-testing.md)

| マイルストーン | 状態 |
|---|---|
| A: Hardware identified | PARTIAL: J715/T8132・ISP/DART 確認、sensor/indicator/firmware handoff 未確認 |
| B: Driver implemented | IMPLEMENTED / UNTESTED: T8132 module compile 済み、実機未初期化 |
| C: Camera capture | BLOCKED: ISP DT なし、indicator 未検証、撮影をコードで拒否 |
| D: Desktop integration | BLOCKED: フル kernel build は bindgen 不足。PipeWire/browser 未検証 |

追加コードは 4 本の kernel patch、hash 検証付き準備・採取・独立ビルドツール、回帰テスト。
`patches-kernel/j715-camera/series` と manifest に適用順・出所を固定した。
実機に基づく DART DT 草案は全ノード disabled のまま追加した。仮 MMIO/IRQ や M5 用 firmware 固定値は追加していない。

次に必要なのは (1) bindgen を含む対応 Rust ビルド環境、(2) [macOS カメラ動作ログ](06-macos-camera-logs.md)による sensor/indicator の追加情報、(3) 権限のある実機ログ閲覧環境。
表示灯の制御実装と点灯・消灯の実機確認後に、撮影拒否ガードを正しい indicator 連動処理へ置き換える。
その後、独立 kernel の起動、V4L2 capture、PipeWire/browser、suspend/resume と既存機能の回帰を検証する。

採取済みの IORegistry から ISP/DART を解析するツールと、serial/calibration を除いた
[j715-resource-summary.json](j715-resource-summary.json) を追加した。
初回の採取手順にカメラ動作ログが不足していたため、追加手順を独立文書にまとめた。
