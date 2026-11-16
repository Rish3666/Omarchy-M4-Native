# 実装とビルド統合

状態: T8132 ISP 移植と J715 撮影拒否ガードは **IMPLEMENTED / UNTESTED（実機未検証）**。
通常・KUnit 込みの module build は成功。J715 の有効な ISP DT と適合 setfile は **NOT IMPLEMENTED / BLOCKED**。

`patches-kernel/j715-camera/series` の適用順:

1. `0001-isp-h17-prerequisites.patch`: 固定 Aurora snapshot の汎用 H17 前提。
2. `0002-isp-t8132-upstream.patch`: #421 の ISP 部分。T8132/DAPF/再起動・IOVA・sensor tuning・V4L2 等。
3. `0003-j715-block-unverified-capture.patch`: J715 で privacy_blocked を設定。
   STREAMON は firmware 起動・DMA buffer 提出より前に -EACCES を返す。
   DT フラグや module parameter による解除手段は設けない。
4. `0004-isp-copy-payload-within-message-object.patch`: 新 Clang の FORTIFY 警告を修正。
   56-byte payload の読み出し元を arg1 単独のフィールドから完全な message object 内へ変更。
   arg0 を最後に書く DMA barrier の順序は維持。隣接 slot を壊さない KUnit ケースも追加。

5. `0005-dart-static-stream-remaps.patch`: 旧 7.1.9 DART へ unlocked static remap を限定 backport。
   不正 pair・chain・static source の consumer 指定を拒否し、locked root への新規設定は -EOPNOTSUPP。
   reset 後に source TCR のみへ remap を設定し、IOMMU bypass は使わない。
   KUnit は malformed mapping、locked-root 拒否、source TCR 以外のメモリー不変を検証する。

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
# この対話のローカル Linux では bindgen 不足で失敗した。ユーザー VM は別途検査する。
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

追加実装（macOS 実機採取後）:

- `tools/camera-m4-hardware.py`: arm-io address translation、DART instance/DAPF、firmware segment、
  PMGR virtual/physical を区別して解析し、IOService と上流 T8132 の値を照合する。
- `dts/camera-m4/t8132-j715-dart-resources.dtsi`: 実機値に基づく3つの DART resource 草案。
  全ノード disabled、production DTS と kernel patch series へは未組込。
  power domain と backend remap/locked-root 対応を検証する前に有効化してはならない。
  未確定の ISP mailbox/clock と、boot-dependent firmware reserved-memory は追加していない。

この草案は既存 J715 DTS と合わせて cpp/dtc でコンパイルできた。
既存ノードの property はすべて不変で、追加は無効な3つの DART ノードだけであることを比較確認した。

追加ログ後の実装:

- hardware tool に `--camera-log` / `--active-registry` を追加し、数値 ID とモデル名の一致から
  IMX958 を識別する。片方のみ・複数 ID の混在では型番を確定しない。
  mode/geometry/state だけを抽出し、setfile revision と indicator 方式を勝手に推定しない。
- prepare ツールは DART C/Kconfig/新規 KUnit source の base hash も検査し、5パッチ全体の
  適用後 hash を確認してから完全 kernel コピーを作る。
  実行済みの最新ツリーは `/home/kazu/Work/camera-build/t8132-kernel-remap`。
- `dts/camera-m4/j715-imx958-preview-presets.dtsi` に config 6 / processed 3040x2880 に基づく
  1280x720 の実験 preview を追加した。crop は中央の 880,1080,1280,720 として計算した 1:1 crop。
  **macOS で観測した出力 crop ではなく、未検証の開発用選択**。まだ有効な ISP node に組み込まない。

DART の KUnit は source TCR だけを書き、隣接領域を保持することを memory-backed register で検査する構成。
今回確認したのは test source の compile/link までで、KUnit の実行と IOMMU 実機試験は未実施。
