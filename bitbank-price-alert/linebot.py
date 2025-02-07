import os
import requests
import json
import time
import logging
import pytz
from datetime import datetime

from utils.constants import *

# 日本時間を設定
japan_timezone = pytz.timezone('Asia/Tokyo')

# 対象通貨
CURRENCY_PAIR = os.getenv("CURRENCY_PAIR")
# LINE APIのエンドポイント
URL = os.getenv("LINE_URL")
# チャンネルアクセストークン
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
# 送信先ID
TO = os.getenv("LINE_USER_ID")

# リトライ回数の設定
MAX_RETRIES = int(os.getenv("MAX_RETRIES"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY"))  # 秒

# ログの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# LINEにメッセージを送信する関数
def send_message(current_price, alert_target_prices):
    alert_prices_message = ""
    for price in alert_target_prices:
        alert_prices_message += f"\n・{CURRENCY_PAIR} : {price}{CURRENCY_UNIT[CURRENCY_PAIR]}"

    # ヘッダーの設定
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    }

    # 日本時間に変換
    now = datetime.now(japan_timezone)
    today = now.strftime("%Y/%m/%d %H:%M:%S")

    text = f"[価格通知 {today}]\n"
    text += f"現在の価格 : {current_price}{CURRENCY_UNIT[CURRENCY_PAIR]}\n"
    text += LINE
    text += "\n各アラート価格"
    text += alert_prices_message

    # 送信データ
    data = {
        "to": TO,
        "messages": [
            {"type": "text", "text": text}
        ]
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # POSTリクエストを送信
            response = requests.post(URL, headers=headers, data=json.dumps(data), timeout=10)
            response.raise_for_status()  # HTTPエラーを検出
            return True  # 成功したら終了
        except requests.exceptions.RequestException as e:
            logger.error(f"メッセージ送信失敗 ({attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)  # リトライ前に待機
            else:
                logger.error("最大リトライ回数に達しました。処理を中断します。")
                return False  # 最終的に失敗した場合
