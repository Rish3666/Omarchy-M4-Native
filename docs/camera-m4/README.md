# M4 MacBook Air 15-inch（J715）カメラ開発

現在: **PARTIAL / BLOCKED**。カメラの初期化・実フレーム取得は達成していない。
実機は J715/T8132 と確認した。ISP DT ノード、T8132 ドライバー、確認済み setfile、
表示灯情報が不足している。既存カーネル・起動環境は変更していない。

- [環境](01-environment.md)
- [上流分析と実コミット](02-upstream-analysis.md)
- [ハードウェア識別・macOS 採取](03-hardware-identification.md)
- [実装・ビルド・ロールバック](04-implementation.md)
- [実際の検証結果・実機試験手順](05-testing.md)

| マイルストーン | 状態 |
|---|---|
| A: Hardware identified | PARTIAL: J715/T8132 確認、sensor/ISP resources/firmware 未確認 |
| B: Driver implemented | BLOCKED: 上流ソースの Git 取得不可、移植なし、indicator 未検証 |
| C: Camera capture | BLOCKED: /dev/video* なし、取得なし |
| D: Desktop integration | BLOCKED: camera 未初期化、実験ビルド補助のみ実装 |

実装したコードは情報採取・隔離 fetch・独立ビルドの補助とテスト。
ドライバー追加や Device Tree の仮値による有効化はしていない。
一般ストリーミングは表示灯の検証が完了するまでブロックする。

次に必要な外部条件は (1) GitHub に接続できるソース取得環境、
(2) この J715 の macOS IODeviceTree/IOService、(3) 権限のある実機ログ閲覧環境。
その後に依存差分の移植、firmware 抽出、表示灯実装、独立 kernel build、
承認された実機起動試験へ進む。
