# Bitbankの価格をLINEに通知する

# 機能
- 5分間隔でbitbankの価格を監視
- 仮想通貨の目標価格に到達したら1日1回の通知
- 目標価格と比較して大きいか小さいかを判定する
- 最終通知日付が昨日の場合は、08:30 ~ 23:59の間で通知。それ以外は00:00～23:59の間で通知。

# 実際の動作
![実装の動作](./実際の動作.png)

# アーキテクチャ図
![アーキテクチャ図](./bitbank-price-alert.png)

# 環境変数
[環境変数(非公開)](./SECRET.md)

# テーブル構造
[テーブル構造(非公開)](./SECRET.md)

# 通貨ペア
https://github.com/bitbankinc/bitbank-api-docs/blob/master/pairs.md

# BitBankのレートリミット

[頻度制限について基本的に取得系は 10回/秒 、更新系は 6回/秒 としています。](https://github.com/bitbankinc/bitbank-api-docs/blob/master/rest-api_JP.md#%E3%83%AC%E3%83%BC%E3%83%88%E3%83%AA%E3%83%9F%E3%83%83%E3%83%88:~:text=%24ACCESS_SIGNATURE%0A8ef83c2b991765b18c95aade7678471747c06890a23a453c76238345b5c86fb8-,%E3%83%AC%E3%83%BC%E3%83%88%E3%83%AA%E3%83%9F%E3%83%83%E3%83%88,-%E3%83%A6%E3%83%BC%E3%82%B6%E3%81%94%E3%81%A8%E3%80%81%E6%9B%B4%E6%96%B0)

# 構成

<pre>
.
 ┣ 📂.vscode
 ┃ ┗ 📜launch.json
 ┣ 📂bitbank-price-alert
 ┃ ┣ 📂utils
 ┃ ┃ ┗ 📜constants.py     -> 共通部品
 ┃ ┣ 📜lambda_function.py -> メイン処理
 ┃ ┣ 📜linebot.py         -> Lineに通知する
 ┃ ┣ 📜requirements.txt   -> ライブラリリスト
 ┃ ┗ 📜setup.bat          -> Setup
 ┗ 📜README.md            -> README.md
</pre>
