# Airwindows Kome Watcher

Airwindows の新作を12時間ごとに監視し、スマホへ通知しつつ、既存プラグインも発掘できる日本語PWAです。

## できること
- Airwindows 公式RSSを12時間ごとに確認
- 新作は初期状態では全件通知
- Android/iPhone/PCで使えるPWA（ホーム画面追加対応）
- ntfy を使ったスマホPush通知
- Airwindopedia から既存プラグイン一覧を生成
- 「好き / 気になる / まあまあ / 興味なし / 試した」の反応を端末内に保存
- 反応履歴からタグごとの好みをローカル学習し、一覧を並べ替え
- 新作と既存発掘を分離
- UIは日本語
- ChatGPT契約には依存しない

## 構成
- `scripts/update_airwindows.py`: RSS / Airwindopedia の取得・データ生成・通知
- `.github/workflows/watch.yml`: 12時間ごとの定期実行
- `docs/`: GitHub Pages で公開するPWA
- `docs/data/`: 自動生成JSON

## 導入（GitHub）
1. このフォルダを新しいGitHubリポジトリに入れる。
2. Repository Settings → Pages で `GitHub Actions` を選ぶ。
3. Android/iPhone に ntfy を入れ、推測されにくいトピック名を購読する。
4. Repository Settings → Secrets and variables → Actions → New repository secret で `NTFY_TOPIC` を登録。
5. Actions から `Airwindows watcher` を一度手動実行。
6. Pages のURLをスマホで開き、「ホーム画面に追加」。

## 通知時刻
`Asia/Tokyo` で 09:52 / 21:52。`.github/workflows/watch.yml` で変更可能です。

## 好み学習について
v1では好みデータはブラウザの `localStorage` に保存します。つまり、個人の反応はGitHubやChatGPTへ送信しません。
新作通知は取りこぼし防止のため全件送りますが、PWA内では反応履歴に基づいて「コメ向け度」を端末内で計算し、並べ替えます。

将来的に「通知そのものを好みに応じて弱める」には、端末の好みプロファイルを安全に同期する小さなバックエンドが必要です。v1ではプライバシーと壊れにくさを優先しています。

## 日本語要約
外部AI APIなしでも動くよう、カテゴリと本文キーワードから日本語の説明を生成します。より自然な翻訳・要約を使いたい場合は、後から任意の翻訳APIを差し込める設計にしています。

## 注意
- ntfy のトピック名は実質的に秘密情報です。短い一般名にしないでください。
- GitHub Actions のスケジュールは混雑時に多少遅れることがあります。
