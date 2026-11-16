# macOS のカメラ動作ログ採取

最初の IORegistry 採取だけでは J715 の sensor/module ID と indicator 機構を特定できなかった。
追加で appleh16camerad と AppleH16CameraInterface の動作ログを採る。
この手順は **macOS 上** で実施する。Linux の撮影ガードを解除するものではない。

1. Photo Booth、FaceTime、ブラウザーなどカメラを使うアプリを終了する。
2. ターミナルで以下を実行する。ログ取得中はコマンドが終了しない。

```sh
mkdir -p ~/Desktop/j715-camera-inspection
sudo /usr/bin/log stream --style compact --level debug \
  --predicate 'process == "appleh16camerad" OR senderImagePath CONTAINS[c] "AppleH16CameraInterface"' \
  > ~/Desktop/j715-camera-inspection/appleh16camerad-live.log \
  2> ~/Desktop/j715-camera-inspection/appleh16camerad-live.stderr.txt
```

3. Photo Booth を手動で開き、プレビュー映像を20秒ほど表示する。シャッターを押す必要はない。
   表示灯が点灯するか、物理 LED なのか画面上のマークなのかを観察する。
4. プレビュー表示中に **別のターミナル** で次を実行する。

```sh
/usr/sbin/ioreg -r -c AppleH16CamIn -l -w0 \
  > ~/Desktop/j715-camera-inspection/AppleH16CamIn-active.txt
```

5. Photo Booth を終了し、表示灯が消えるか確認する。数秒後に最初のターミナルで Ctrl+C を押す。
6. `appleh16camerad-live.log`、`appleh16camerad-live.stderr.txt`、`AppleH16CamIn-active.txt` を、
   前回と同じ Transfer の `j715-camera-inspection` フォルダーへコピーする。
   点灯・消灯と表示場所の観察結果も記録する。

コマンドが失敗した場合も stderr ファイルを残す。
ログにセンサー型番が必ず出るとは限らない。空または `<private>` の場合はそのまま扱い、
privacy 設定の無効化やシステム全体の logging 設定変更は行わない。
ログや IORegistry には module serial などが含まれ得るため、元ファイルは公開 Git に追加しない。

macOS で表示灯が動いたという観測だけで、Linux の表示灯制御が検証できたことにはならない。
得られた情報に合わせて indicator 制御を実装し、Linux でも start/stop/failure を検証する必要がある。

CLI の概要: [Apple WWDC — Unified Logging and Activity Tracing](https://devstreaming-cdn.apple.com/videos/wwdc/2016/721wh2etddp4ghxhpcg/721/721_unified_logging_and_activity_tracing.pdf)。
当該 macOS のオプションは `man log` または `/usr/bin/log help stream` でも確認できる。
