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
- 公式の英語説明をアプリ内で全文表示し、無料のオフライン翻訳で日本語訳を順次追加
- ChatGPT契約には依存しない

## 構成
- `scripts/update_airwindows.py`: RSS / Airwindopedia の取得・データ生成・通知
- `.github/workflows/watch.yml`: 12時間ごとの定期実行
- `.github/workflows/test-notification.yml`: ntfy の手動テスト通知
- `scripts/translate_descriptions.py`: 公式説明の英語→日本語翻訳
- `requirements-translate.txt`: 翻訳ライブラリのバージョン指定
- `docs/`: GitHub Pages で公開するPWA
- `docs/data/`: 自動生成JSON

## 導入（GitHub）
1. このフォルダを新しいGitHubリポジトリに入れる。
2. Repository Settings → Pages で `GitHub Actions` を選ぶ。
3. Android/iPhone に ntfy を入れ、推測されにくいトピック名を購読する。
4. Repository Settings → Secrets and variables → Actions → New repository secret で `NTFY_TOPIC` を登録。
5. Actions から `Airwindows watcher` を一度手動実行。
6. Pages のURLをスマホで開き、「ホーム画面に追加」。

## スマホ通知のテスト
1. `.github/workflows/test-notification.yml` を、リポジトリ直下の同じパスに追加してコミットする。既存の `watch.yml` は変更しない。
2. `NTFY_TOPIC` が登録済みなら再登録は不要。スマホの ntfy アプリで同じトピックを購読しておく。変更する場合は Repository Settings → Secrets and variables → Actions → `NTFY_TOPIC` → Update secret を使う。
3. GitHub の Actions → **Test ntfy notification** → **Run workflow** → 緑の **Run workflow** を押す。
4. 実行結果が緑のチェックになり、スマホに「おいでたぞコメくん！うおおお　これはテスト通知です」が届けば成功。

GitHub に手動で追加する場合は、リポジトリ直下で **Add file → Create new file** を選び、ファイル名に `.github/workflows/test-notification.yml` を入力して内容を貼り付け、**Commit changes** を押す。README もこのファイルの内容に差し替える。通知が届かないときは、Actions の実行ログで `Send test notification` を確認し、スマホの購読トピックと `NTFY_TOPIC` の値が一致しているか調べる。

## 通知時刻
`Asia/Tokyo` で 09:52 / 21:52。`.github/workflows/watch.yml` で変更可能です。

## 好み学習について
v1では好みデータはブラウザの `localStorage` に保存します。つまり、個人の反応はGitHubやChatGPTへ送信しません。
新作通知は取りこぼし防止のため全件送りますが、PWA内では反応履歴に基づいて「コメ向け度」を端末内で計算し、並べ替えます。

将来的に「通知そのものを好みに応じて弱める」には、端末の好みプロファイルを安全に同期する小さなバックエンドが必要です。v1ではプライバシーと壊れにくさを優先しています。

## 日本語要約
一覧の短い日本語概要は、カテゴリと本文キーワードから生成します。各カードの「公式説明の日本語訳を読む」を開くと、Airwindows の公式原文を翻訳した詳しい説明が読めます。「公式説明の原文を読む」で英語原文も確認できます。翻訳文は機械翻訳なので、音響用語や操作説明が不自然な場合は原文も参照してください。

翻訳にはオープンソースの Argos Translate を GitHub Actions 上で使用します。翻訳APIキーや有料翻訳サービスは不要です。初回は英語→日本語のモデルをダウンロードし、結果を `docs/data` のJSONに保存します。1回の監視実行で最大100件ずつ翻訳するため、既存プラグイン全件の日本語訳が揃うまでには複数回の実行が必要です。訳がまだないカードでも英語原文は読めます。新着プラグインの翻訳を優先します。

### 追加ファイルの反映手順
GitHub上の既存リポジトリへ更新する場合は、リポジトリ直下を基準に次のファイルを追加・差し替えてコミットしてください。ZIPをそのままアップロードしないでください。

- 差し替え: `.github/workflows/watch.yml`, `scripts/update_airwindows.py`, `docs/index.html`, `docs/app.js`, `docs/styles.css`, `docs/sw.js`, `README.md`
- 追加: `scripts/translate_descriptions.py`, `requirements-translate.txt`

その後、Actions → **Airwindows watcher** → **Run workflow** を1回実行します。実行が成功したらスマホのアプリを再読み込みしてください。翻訳処理に一時的な失敗があっても監視と通知は続き、次回の実行で翻訳を再試行します。

GitHub Actions の標準ランナーは公開リポジトリでは無料です。非公開リポジトリはアカウントの無料枠を消費するため、無料枠を超える設定では料金が発生する場合があります。

## 注意
- ntfy のトピック名は実質的に秘密情報です。短い一般名にしないでください。
- GitHub Actions のスケジュールは混雑時に多少遅れることがあります。
