# J715 camera VM / 実機検証結果

- 日付・担当:
- project commit（PROJECT-COMMIT.txt）:
- base source（同梱 archive / 既存 VM source、hash）:
- VM OS / architecture / vCPU / RAM:
- clang / LLD / LLVM tools version・実行パス:
- rustc / HOSTRUSTC / rustdoc version・実行パス:
- Rust source の版・RUST_LIB_SRC / sysroot:
- bindgen / libclang version・LIBCLANG_PATH:
- preflight: PASS / FAIL（ログ名）
- prepare hash 検査: PASS / FAIL
- Python: 成功 / 失敗 / skip 件数（期待16件）
- olddefconfig 後の差分（Rust/GPU/audio/入力/SSD の保持）:
- full kernel build: 成功 / 失敗 / 未実施
- 最初の error と前後・ログ名:
- kernelrelease / Image・DTB・modules artifact のサイズと SHA256:
- KUnit: compile のみ / 実行済み（環境・kernelrelease）
- KUnit suite ごとの pass / fail / skip、KTAP ログ:
- 実機起動: 未実施 / 成功 / 失敗（復旧経路）
- Linux ISP 初期化 / firmware load / DART faults:
- センサー module/revision と setfile の根拠:
- macOS LED 観測（既知: センサーエリア LED の点灯・消灯）:
- Linux LED 制御・start/stop/failure/halt の結果:
- V4L2 node / format / 実フレーム:
- PipeWire / アプリ / browser:
- GPU/display/audio/入力/SSD 回帰:
- suspend/resume（未実施の場合は理由）:
- 残る問題と次に必要な入力:

元ログ・個体 serial/calibration・秘密鍵を公開 Git に追加しない。
compile 成功を実機動作成功に読み替えず、未実施と失敗を区別する。
