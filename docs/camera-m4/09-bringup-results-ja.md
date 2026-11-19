# J715 カメラの実機での立ち上げ結果（2026-11-17〜19）

対象: 所有者の J715（Mac16,13 / T8132）、Omarchy、ISP firmware 5.502（26.5.1 のスタブ、iBoot mBoot-18000.120.36）。
試験はすべて所有者の承認のもと、ESP の boot.bin を一時的に差し替える方式で行い、毎回元に戻した。
最終的に所有者の判断で、カメラ用の起動環境を常用にした（下の「常用の起動環境」）。

## 結論
- **Linux の V4L2 で J715 の内蔵カメラ（IMX958）から実フレームを取得できた。** `/dev/video0`「FaceTime HD Camera」、
  1920x1080 NV12、約 30 fps、通常のユーザーで使える。PipeWire の Video の Source、ブラウザー（getUserMedia、Brave）、
  mpv での表示、開閉の繰り返し、5分の連続表示を確認した。
- **表示灯はセンサーの電源と連動する。** ISP firmware が `CISP_CMD_CH_START` で PMU（SN657098、I2C）経由でセンサーの
  電源を入れると点灯し、停止で消灯する。ドライバーは表示灯に触れない。すべての撮影で、撮影中だけ点灯した。
- **決め手は ISP の DART の stream の付け替え（patches-kernel/j715-camera/0005）。** 動作中のカーネルの DART ドライバーは
  DT の `apple,remap-streams`（1,2,3,6,7,10,11 → 0）を実装しておらず、ISP の DMA の一部が無効な stream に向かっていた。
  これが次の2つの症状の原因だった。
  1. 撮影時: firmware が `[ERROR] PIODMA[0] Irq Error!`、`ASSERT: CIspEngineExeLoopH16.cpp, 469` で停止し、センサーの
     電源が入ったまま（表示灯が点いたまま）になる。
  2. 初期化時: 起動の約3割〜半分で、firmware が `[tableMem]` のログの後（COMP 領域を埋める前）に止まり、
     最初の IO コマンドに応答しない（ETIME -62）。同じ起動の中では firmware を起動し直しても変わらない。
  付け替えを入れると、初期化は 6 起動中 6 回完了し、撮影も成功した。
- センサーの setfile（`isp_2224_01XX.dat`、magic 0x22240106）が必要。所有者の macOS の `/usr/libexec/appleh16camerad`
  から `tools/extract-imx958-setfile.py` で抽出した。無い場合はドライバーは警告して撮影を続ける。

## 原因から外れたもの（実機の計測で確認）
早すぎる最初のコマンド（1秒待っても同じ）、ANE の電源（ISP の power-domains に追加しても同じ）、ISP/ANE を含む pmgr の
全電源ドメイン（131＋6個、成功・失敗の起動で同一）、firmware の物理配置、firmware の text・data・iBoot の起動パラメーター
（STKG・PACE を成功時の値に置き換えても同じ）、firmware に渡すメモリの物理ページ、ISP firmware の版（26.6.2 の 5.605 と
コマンド・初期化の文字列は同一）。

## 構成要素と再現性
| 要素 | 置き場所 | 確認 |
|---|---|---|
| ISP ドライバー | `patches-kernel/j715-camera/series`（0001〜0006） | 検証済みの base に適用し、guarded の27ファイルすべて一致 |
| 撮影の許可 | 0006: 既定は拒否、`options apple_isp j715_allow_capture=1` で許可 | 実機で確認 |
| DART 付け替え | 0005（カーネルに組み込み） | #16 と同じツリーに 0005 だけを当てた差分ビルド #17。再コンパイルは apple-dart.o のみ、.config 差分なし、symvers 同一。実機で stream 1,2,3,6,7,10,11 の TCR が 0x80 |
| ISP の DT | `dts/camera-m4/t8132-j715-isp.dtsi`、`tools/build-j715-isp-dtb.py` | 試験した DTB（e1e9b6cc…）を1バイトも違わず再生成 |
| loader の ISP 受け渡し | `patches-m1n1/j715-isp-handoff` | stock・backlight・ISP 受け渡しの stage2 を1バイトも違わず再現（m4-gravity-builder） |
| 常用の起動環境 | `packaging/j715-camera/j715-camera-boot.py` | install・check・rollback を実機で使用 |
| setfile | `tools/extract-imx958-setfile.py`（所有者の macOS で実行） | 2224_01 dce21e48…、2226_02 5e2e5c4a… |

## センサーの設定
- config 5（J713 と同じ、読み出し 1920x1080、入力 1920x2160）: 向き・色・露出とも正常。**当面の既定**。
- config 6（J715 の macOS と同じ、読み出し 3040x2880、入力 3040x5760）: 画角は広いが、四隅の減光と樽型のゆがみが大きい。
  macOS はゆがみ補正（`CISP_CMD_CH_TILE_GDC_ENABLE` など）を使うと推定。補正を有効にできたときの候補。

## 表示灯が消えなくなった場合
firmware が停止の要求に応答しないまま止められると、センサーの電源が入ったままになり表示灯が残る。再起動・`poweroff`・
電源ケーブルを外す・普通の電源投入では消えず、**電源ボタン長押しで起動オプションを表示させると消える**（2026-11-18 に確認）。
付け替えを入れてからは発生していない。0006 は、この場合にカーネルログで復旧方法を案内する。

## 常用の起動環境
`packaging/j715-camera/README.md` 参照。stage2（バックライト＋ISP 受け渡し）、カーネル #17、ISP の DT を ESP の boot.bin に
入れ、bootargs と initramfs はそのまま。`rollback` で切り替え前に戻せる。J715 の試験ビルドは omarchy-m4-update の対象外で、
boot.bin を自動で書き換える仕組みは無い。

## 残る課題
- スリープからの復帰（J715 の試験ビルドで suspend 自体に既知の問題あり）。
- 画質: ノイズの低減、config 6 のゆがみ補正。
- 0005 は動作中のカーネルへの差分ビルドとして適用した。チャンネルで配る正式なカーネルへの取り込みは未実施。
