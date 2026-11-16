# 実装とビルド統合

状態: 補助ツール **IMPLEMENTED / UNTESTED（一部実行済み）**。
カメラドライバー移植・DT・setfile は **NOT IMPLEMENTED / BLOCKED**。

追加した実装:

- `tools/camera-m4-inspect.py`: Linux DT、モジュール、V4L2/PipeWire の状態を読み取り専用で収集。
  任意の ADT から許可したリソース情報を抽出し、calibration を出力しない。capture device は開かない。
- `tools/camera-m4-fetch.sh`: #421/#422/#208 を隔離 bare リポジトリへ取得。
  T8132 の確認済みコミットを ancestry 検証し、取得した refs を保存。
- `tools/build-j715-camera.sh`: レビュー済みの移植先カーネル Git ツリーから
  実験用 Image/modules/DTB のオフライン tar を作成する。
  Git にない現在の kbuild を、出所確認なしで製品ソースとして使わない。
- `tests/test_camera_m4_inspect.py`: DT エンディアン保持・private data 除外・ADT 入力終端を検証。

実験用ビルド（ソースを取得・移植・レビューし、全変更を commit した後）:

```sh
CAMERA_BUILD_JOBS=8 bash tools/build-j715-camera.sh /path/to/reviewed/kernel-git /path/to/new-camera-build
```

`.config` は移植先ツリーで事前に準備する。外部の組み込み initramfs を指す設定は、別途の資産レビューが必要なため拒否する。ソースは清浄な Git ルートである必要がある。
T8132 OF match がない場合は停止する。この文字列チェックは完全な依存関係や indicator の検証ではない。
ネイティブ aarch64 / LLVM を使用。Rust 有効時は kbuild の rustavailable も確認する。
ツールチェーン全体を固定したコンテナーで再現ビルドする必要がある。
既存 J715 build 18 の特殊な証明書・initramfs・バイト一致条件は、この実験ツールで再現したとは主張しない。

`-omarchy-m4-camera-test` をリリース名へ付加し、独立ディレクトリに展開してビルドする。
modules_install は専用 stage に限定し、depmod の実機実行はしない。
成果物は未署名の実験用 tar。起動可能なディストリビューションパッケージではなく、
既存 initramfs・m1n1 chain との結合も未検証。
フルビルドと成果物再現性は未検証。SOURCE_DATE_EPOCH とアーカイブ所有者・時刻は固定するが、
絶対パスや Rust metadata を含む再現性までは保証しない。

タスクの「実験用カーネルを分離する」という明示指示に従い、実験成果物は通常 channel と分離した。
一般配布する段階では CONTRIBUTING.md に従い、omarchy-m4-update/channel で提供し、
package release/hash、音声・映像の再認証を更新する。
未検証 kernel を channel に登録する変更や既存 PKGBUILD の書換えは行っていない。

ロールバック: 現状はシステムに何も導入していないため不要。
作業コピーと `/home/kazu/Work/camera-build` の成果物だけを削除できる。
将来の実機起動テスト前には、known-good kernel/modules/DTB/boot chain の hash と
実際に起動できる復旧エントリーを別途確認する。
その後も実験イメージを別名で配置し、承認済みの一回限りの選択から起動する。
既定エントリー変更、NVRAM/EFI 変数更新、firmware flash は本ツールの対象外。
