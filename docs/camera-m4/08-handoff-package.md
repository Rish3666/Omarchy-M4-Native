# 引継ぎセットと Transfer コピー結果

## 作成物

作業領域の出力先:

- `/home/kazu/Work/j715-camera-handoff-20261116/`
- `/home/kazu/Work/j715-camera-handoff-20261116.tar.gz`
- `/home/kazu/Work/j715-camera-handoff-20261116.tar.gz.sha256`

入口は引継ぎセット直下の `START-HERE-ja.md`。
これは `07-handoff-instructions-ja.md` のコピーであり、VM 環境・依頼履歴・調査結果・実行手順をまとめた。
project の固定 commit はセット内 `PROJECT-COMMIT.txt`、全同梱ファイルの検査は `SHA256SUMS`。

| 内容 | 保存先 |
|---|---|
| 指示書・解析・sanitized summary・パッチ・ツール・テスト | project/ |
| 開発ブランチの Git 履歴 | project.bundle |
| 元の依頼全文 | j715-Camera-Task.md |
| 参考7.1.9 source（圧縮、約170MiB） | inputs/kernel-base-7.1.9-camera-reference.tar.xz |
| 元 target config / reference symvers | inputs/base.config / reference-Module.symvers |
| 基準 source の公開証明書のみ | inputs/base-signing-certificate.pem / CERTIFICATE-INFO.json |
| 除外物・clean 方法と制約 | inputs/BASE-CLEANUP.json |
| PR #421/#422 の確認用 source 抜粋 | upstream/ |
| 実行済み compile/link 等のログ | evidence/ |
| 次の担当者の結果記入用 | VM-RESULTS-TEMPLATE.md |
| 同梱 manifest | FILE-LIST.txt / SHA256SUMS / BUNDLE-INFO.json |

参考 source には元々 Documentation/Makefile 等が省略されている。
フルビルドを確認済みの完全な upstream checkout ではなく、VM の既存ソースとの比較・fallback 用。
生成済みの署名用秘密鍵と prebuilt ELF は除外した。元 source の署名 PEM から公開証明書だけを取り出した。
raw camera 資料は既存の Transfer 上 `j715-camera-inspection/` を利用し、セット内では重複させていない。
Apple firmware、setfile、per-module calibration、生成済み kernel/.ko は同梱しない。
Clang/Rust/bindgen 本体や VM image も含めず、ユーザーの既存 VM 環境を利用する。

## Transfer の実際の状態

依頼された `/mnt/Transfer` はこの Linux 環境では存在せず、実際の mount は **`/mnt/transfer`**。
`findmnt -T /mnt/transfer` は **exfat / ro** を返した。
指示書を新規作成でコピーしようとしたところ、`Errno 30: Read-only file system` で失敗した。
そのため **このセッションから Transfer へのコピーは完了していない**。
mount 変更・filesystem 修復・既存データの上書きは行っていない。

書き込み可能な環境になった後に、Linux 側で以下を実行できる:

```bash
cp -n /home/kazu/Work/j715-camera-handoff-20261116.tar.gz \
      /home/kazu/Work/j715-camera-handoff-20261116.tar.gz.sha256 /mnt/transfer/
cd /mnt/transfer
sha256sum -c j715-camera-handoff-20261116.tar.gz.sha256
```

書き込み先に同名ファイルが既にある場合は、先に checksum を確認し別版と混同しない。
macOS 側の volume path は通常 `/Volumes/Transfer` だが、実際の表示名を確認する。
圧縮 source の展開は Transfer ではなく ARM64 Linux VM 内の filesystem で行う。
