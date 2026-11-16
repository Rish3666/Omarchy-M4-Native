# 上流 ISP 変更の分析

状態: **PARTIAL / BLOCKED**。GitHub PR 本文・コミットリンクの閲覧はできたが、
Git fetch、patch URL、raw ソースの取得に失敗した。全差分・全前提のレビューと適用は未完了。
コミット番号は PR の実際のリンクから得たもので、ローカル Git オブジェクトの検証は未実施。

| Component | Existing support | Missing changes | Source commit |
|---|---|---|---|
| ISP core | 7.1.9 の旧 Apple ISP | H17 と前提変更全体の移植確認 | PR #421 全体（未取得） |
| T8132 support | OF match なし | T8132 設定と再起動処理 | 5f3511a0e7e93395a83273946947e84cb93bf593 |
| DART | t8132-dart は稼働 DT に存在、ISP 用は未確認 | ISP の address filter | 00e88f127ec23bee3605e54c7bd9338ff022980f |
| 電源 | T8132 ISP 非対応 | ストリーム間の停止・再開 | a17e540a0df57cb4b304b15212a5f3eb5de45037 |
| Camera sensor | J715 の型番不明 | 実機 module/sensor ID の照合 | 未確定 |
| Firmware | 古いモデル用 setfile のみ確認 | J715 用 setfile・予約メモリーの確認 | 未確定 |
| Device Tree | J715 DTS はあるが ISP がない | 実機 ADT に基づく記述 | 未確定 |
| V4L2 | モジュール設定は有効 | ISP 登録と実フレーム検証 | 未確定 |

[PR #421](https://github.com/omacom/linux-aurora/pull/421) は T8132、T8142、T6040 と
H17 関連変更を含む。T8132 は T6040 系の起動経路を利用するが、AMCC 数などが異なる。
DART のフィルターは電源投入ごとに設定する必要があり、単に IOMMU を無効にして代用してはならない。
再起動にはデータ領域の復元と coprocessor の quiesce が関わる。
T8132 用変更は M5 固有の GPIO を流用する理由にはならない。

[PR #422](https://github.com/omacom/linux-aurora/pull/422) は J714c/T6050 の実装であり、
J715 対応とは異なる。表示灯制御も同 PR の実機情報に依存する。T8132 の DT、表示灯、
ファームウェアが揃うことは、当該ドライバーの追加だけでは保証されない。
T8142/T6050 と T8132 のレジスター・DMA・全プロトコル差分はソース取得後のレビュー対象。

[installer PR #208](https://github.com/omacom/omarchy-mac-installer/pull/208) の
`cffff8b5ed2cbaa8dd52233188251e9d3791ef85` は IMX958 用 setfile の抽出登録を追加する。
J715 に適用するセンサー一致の根拠は得られていないため、抽出済みファイルの流用や登録追加はしない。

[M5 開発記事](https://joshuawarren.com/blog/omarchy-on-the-m5-max-macbook-pro/) も参照したが、
J715 のハードウェア設定の一次資料には用いない。

ネットワークが利用できる環境で:

```sh
bash tools/camera-m4-fetch.sh /tmp/j715-upstream-new
# 各 *.refs の完全 SHA を記録し、以後のレビュー・ビルドはその SHA に固定する。
git --git-dir=/tmp/j715-upstream-new/linux-aurora.git log --oneline pr-421
git --git-dir=/tmp/j715-upstream-new/linux-aurora.git show 5f3511a0e7e93395a83273946947e84cb93bf593
```

fetch ツールは専用 bare リポジトリに保存し、既存ブランチを変更しない。
PR head は変動するため、取得結果を再現用 lock として保存する。
#421 の親履歴と #422 の merge-base を比較し、H17、firmware reserved-memory、
DMA/IOVA、電源、KUnit の前提を一覧化した後に最小差分を移植する。
現在のカーネルツリーに Git がないため、同一コミット有無の証明はできない。
ただしソース・インストール済みモジュール双方に T8132 match がないことは確認した。

再利用済み上流コード: **なし**。コミットリンクの確認を移植完了とは報告しない。
