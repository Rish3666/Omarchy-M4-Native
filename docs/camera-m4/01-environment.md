# J715 実行環境（2026-11-16）

状態: **PARTIAL**。以下の初期調査に加え、PR #421/#422 をローカルから参照可能になった。
移植・ビルドの最新結果は 04/05 を参照。システム全体の DNS 制限とは扱わない。

| 項目 | 観測結果 |
|---|---|
| model | Apple MacBook Air (15-inch, M4, 2025) |
| compatible | apple,j715 / apple,t8132 / apple,arm-platform |
| uname -r | 7.1.9-m4-gpu-backport-20261008 |
| カーネルビルド | #16 SMP PREEMPT_DYNAMIC、2026-10-15 |
| アーキテクチャ | aarch64、nproc=10 |
| 設定 | CONFIG_MEDIA_SUPPORT=m / CONFIG_VIDEO_DEV=m / CONFIG_VIDEO_APPLE_ISP=m |
| ビデオノード | /dev/video*、/dev/media* とも存在しない |
| ISP DT | 稼働中の /proc/device-tree に ISP/camera ノードを確認できない |
| 既存 ISP モジュール | apple-isp.ko。modinfo に t8132-isp alias がない |
| firmware | apple/isp_1820_01XX.dat、1922_02XX、8723_01XX、8720_01XX、1921_01XX、1822_02XX |
| コンパイラー | Clang 23.1.4、Rust 1.99.1 |

元リポジトリ: `/home/kazu/j715/upstream-repo`、origin は
https://github.com/Kb2uka/Omarchy-M4-Native 。develop は
`7d107f95bff1bc32efb2dd0fd019f9f4c1dba6a3`。未追跡の Python キャッシュがあるため元ツリーは変更しない。
`/home/kazu/Work/Omarchy-M4-Native` にローカル clone を作り、
`camera/j715-isp-bringup` で作業した。clone の origin は元ローカルパスを指す。

既存カーネルソースは `/home/kazu/j715/kbuild`。7.1.9 の設定済み・ビルド済みツリーで、Git 管理情報はない。
稼働バイナリーとのソース一致までは証明できない。`/usr/src` にソースや headers はない。
既存再現手順は `tools/build-j715-kernel.sh`。build 18 のアーカイブ SHA256、
Clang 21.1.8 / Rust 1.93.1 を固定しており、今回の実機 build 16 と同一とは扱えない。

`/proc/cmdline` は maxcpus=10、idle=nop、panic=0 と M4 入力・PCIe デバッグ設定を含む。
起動設定の編集はしていない。`/boot/efi` は読み取り権限がなく、復旧用エントリーの実在は未検証。
`chosen/asahi,os-fw-version` は `unknown`。

制限:

- `git ls-remote` と専用 fetch スクリプトは、この実行環境では `Could not resolve host: github.com` で失敗。DNS 制限と断定したのは誤り。ユーザーの通常端末では clone に成功している。
- dmesg は Operation not permitted。sudo は no-new-privileges により使用不可。
- wpctl はセッション・システムバスに接続できず失敗。サービス停止を意味しない。
- フル ADT、J715 カメラ固有の macOS 情報は今回の探索範囲では発見できなかった。

再採取: `python3 tools/camera-m4-inspect.py > /tmp/j715-camera.json`。
生データは `/home/kazu/Work/camera-build/environment.json` に保存し、個人環境情報を含み得るため Git に追加しない。

追記（ユーザーの clone 後）: `/home/kazu/Work/linux-aurora` を確認した。
`integration/aurora` は `39d5f88ab4e54bb61eecd3fba79e3242005f2f76`、作業ツリーは清浄。
このブランチには H17/T8140 対応があるが T8132 ISP 対応はない。
こちらでの PR #421/#422 fetch は同じ名前解決エラーで失敗した。
システム全体の DNS や通常端末の接続障害とは扱わない。

PR の追加 fetch 後: origin/pr-421 は af2676a9ee596bc94bb016d52a925ce550c46963、
origin/pr-422 は 8916070002f4dc60e1bca6995b9c52fa0131683f。
参照のみで、ユーザーの linux-aurora の作業ブランチは切り替えていない。
フルビルド事前検査では bindgen が見つからず rustavailable が失敗した。

macOS 採取後: 27.2.1（26B131）、Mac16,13/J715AP。ISP firmware 6.105 の
ロードを IOService で確認した。Linux の firmware load 成功を意味しない。
raw 採取ファイルは `/mnt/transfer/j715-camera-inspection` にあり、公開 Git へ追加していない。
