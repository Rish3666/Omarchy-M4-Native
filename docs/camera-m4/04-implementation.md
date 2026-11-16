# 実装とビルド統合

状態: T8132 ISP 移植と J715 撮影拒否ガードは **IMPLEMENTED / UNTESTED（実機未検証）**。
通常・KUnit 込みの module build は成功。J715 DT と setfile は **NOT IMPLEMENTED / BLOCKED**。

`patches-kernel/j715-camera/series` の適用順:

1. `0001-isp-h17-prerequisites.patch`: 固定 Aurora snapshot の汎用 H17 前提。
2. `0002-isp-t8132-upstream.patch`: #421 の ISP 部分。T8132/DAPF/再起動・IOVA・sensor tuning・V4L2 等。
3. `0003-j715-block-unverified-capture.patch`: J715 で privacy_blocked を設定。
   STREAMON は firmware 起動・DMA buffer 提出より前に -EACCES を返す。
   DT フラグや module parameter による解除手段は設けない。
4. `0004-isp-copy-payload-within-message-object.patch`: 新 Clang の FORTIFY 警告を修正。
   56-byte payload の読み出し元を arg1 単独のフィールドから完全な message object 内へ変更。
   arg0 を最後に書く DMA barrier の順序は維持。隣接 slot を壊さない KUnit ケースも追加。

元ソースの著作権・ライセンス表記は保持している。
T6050 の GPIO、firmware 予約物理アドレス、センサー設定は含めない。
0002 は複数モデル向けの既存 upstream 変更を含むが、J715 固有ガードは独立させた。
他モデルの実機回帰検証は未実施。

ツール:

- `camera-m4-inspect.py`: Linux/ADT のリソースを許可リストで抽出。ADT identity、segment-ranges、DAPF 等も出力する。
  calibration や serial は出力しない。capture device は開かない。
- `camera-m4-fetch.sh`: 専用 bare リポジトリへの #421/#422/#208 取得と ref 保存。
- `prepare-j715-camera.py`: 対象 ISP の base hash を確認し、temp 上で全パッチを適用して最終 hash を確認。
  成功後に元カーネルを新ディレクトリへコピーし、変更済み ISP ソースを配置する。
  出力先の上書きと元ツリー内への再帰コピーは拒否。
  release を -omarchy-m4-camera-test に分離し、Rust/GPU/audio の有効設定は保持する。
- `build-j715-camera.sh`: レビュー・commit 済みの完全な kernel Git snapshot から独立した Image/modules/DTB tar をビルド。
  Rust は olddefconfig の前に依存を検査し、olddefconfig によって無効化された場合も停止する。

再現手順:

```sh
python3 tools/prepare-j715-camera.py /home/kazu/j715/kbuild /path/to/new-camera-source
# bindgen がない現在の環境では次の事前検査が失敗する。
make -C /path/to/new-camera-source ARCH=arm64 LLVM=1 rustavailable
```

実行済み出力は `/home/kazu/Work/camera-build/t8132-kernel-final`。
base の ISP 全ファイルと最終 ISP の hash は manifest、パッチ hash・入力 config/Makefile hash は
出力ツリーの camera-preparation.json に記録する。
元 kbuild の upstream Git commit は不明であり、完全なソースの再現性まで確立したとは扱わない。

フルビルドには bindgen、互換 Rust/LLVM、必要な rust-src と、レビューした完全な kernel Git snapshot が必要。
clone 済み Aurora kernel 全体への乗り換えは、既存 M4 GPU/audio backport の互換性を保証しないので行っていない。
ソース全体の出所を確認して commit した後は以下を使える（現状は未完了）:

```sh
CAMERA_BUILD_JOBS=8 bash tools/build-j715-camera.sh /path/to/reviewed/kernel-git /path/to/new-camera-build
```

このビルダーは modules_install を専用 stage に限定し、実機 depmod・起動設定変更は行わない。
外部 built-in initramfs を含む構成は追加の資産レビューが必要なため拒否する。
未署名の実験 tar はディストリビューションの導入用パッケージではなく、initramfs/m1n1 chain の結合も未検証。
ビルド時刻・tar 所有者・時刻を固定するが、Rust metadata と絶対パスを含むバイト一致までは未検証。

一般配布時は CONTRIBUTING.md の omarchy-m4-update/channel と package release/hash 更新に従う。
未検証 kernel を channel に登録したり、既存 PKGBUILD を変更したりはしていない。

ロールバック: システムへインストール・ロード・起動変更をしていないため不要。
生成した作業コピーだけを除去できる。将来の起動試験前には known-good kernel/modules/DTB/boot chain の
hash と復旧エントリーからの実起動を確認し、別名の実験成果物を一回だけ選択して試す。
既定 boot entry の変更、NVRAM/EFI 更新、firmware flash は行わない。
