import os
import sys
import boto3
import python_bitbankcc
import logging
import pytz

from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from linebot import send_message

from utils.constants import *

# 対象通貨
CURRENCY_PAIR = os.getenv("CURRENCY_PAIR", None)
# テーブル名
TABLE_NAME = os.getenv("TABLE_NAME", None)

# ログの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#無いならエラー
if CURRENCY_PAIR is None:
    logger.error('Specify CURRENCY_PAIR as environment variable.')
    sys.exit(1)
if TABLE_NAME is None:
    logger.error('Specify TABLE_NAME as environment variable.')
    sys.exit(1)

# 日本時間を設定
japan_timezone = pytz.timezone('Asia/Tokyo')


def lambda_handler(event, context):

    if CURRENCY_PAIR not in CURRENCY_UNIT:
        logger.error(f"対象通貨が不正です: {CURRENCY_PAIR}")
        sys.exit(1)

    try:
        # public API classのオブジェクトを取得
        pub = python_bitbankcc.public()

        current_price = float(pub.get_ticker(CURRENCY_PAIR)["last"])
        logger.info(f"現在の価格: {current_price}")
    except Exception as e:
        logger.error(f"価格取得に失敗しました: {e}")
        sys.exit(1)

    dynamodb = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')

    partition_key_value = CURRENCY_PAIR
    table = dynamodb.Table(TABLE_NAME)

    # queryの実行
    try:
        response = table.query(
            KeyConditionExpression='symbol = :symbol',  # パーティションキーを指定
            ExpressionAttributeValues={
                ':symbol': partition_key_value  # パーティションキーの値
            }
        )

        if response['Count'] == 0:
            logger.info('レコードが存在しません')
            sys.exit(1)
    except ClientError as e:
        logger.error(f"DynamoDBクエリに失敗しました: {e}")
        sys.exit(1)

    items = response.get('Items', [])
    sorted_items = sorted(items, key=lambda x: float(x['target_price']), reverse=True)
    # 現在の時刻を取得
    now = datetime.now(japan_timezone)

    today_formatted = now.strftime('%Y-%m-%d')
    yesterday_formatted = (now - timedelta(days=1)).strftime('%Y-%m-%d')

    # トランザクション更新処理(通知未送信に更新)
    try:
        update_transactions = []  # トランザクションリスト

        for item in items:
            if item['notification_sent'] and item.get('updated_at') != today_formatted:
                update_transactions.append({
                    'Update': {
                        'TableName': TABLE_NAME,
                        'Key': {
                            'symbol': {'S': item['symbol']},
                            'target_price': {'S': item['target_price']}
                        },
                        'UpdateExpression': 'SET notification_sent = :notification_sent, \
                                                updated_at = :updated_at',
                        'ExpressionAttributeValues': {
                            ':notification_sent': {'BOOL': False},
                            ':updated_at': {'S': today_formatted}
                        }
                    }
                })

                item['updated_at'] = today_formatted
                item['notification_sent'] = False

        if update_transactions:
            dynamodb_client.transact_write_items(TransactItems=update_transactions)  # トランザクション実行
    except ClientError as e:
        logger.error("トランザクション処理に失敗しました。自動的に元の状態に戻されました:", e)
        sys.exit(1)

    # 通知対象のアイテムを取得
    alert_target_prices = []
    notified_items = []
    for item in sorted_items:
        target_price = float(item['target_price'])

        if item['target_comparison'] not in ('low', 'high'):
            logger.error(f"比較対象が不正です: {item}")
            sys.exit(1)

        comparison_result = current_price < target_price if item['target_comparison'] == 'low' else current_price > target_price

        if not item['notification_never_sent'] \
            and not item['notification_sent'] \
            and comparison_result:

            should_notify = item['last_notification_date'] != yesterday_formatted or \
                            (item['last_notification_date'] == yesterday_formatted and
                            (now.hour > 8 or (now.hour == 8 and now.minute >= 30)))

            if should_notify:
                notified_items.append(item)
                alert_target_prices.append(target_price)

    # 通知処理
    if len(alert_target_prices) > 0:
        # 通知処理
        logger.info('通知処理を実行します')
        notification_sent = send_message(current_price, alert_target_prices)
        if not notification_sent:
            logger.error('通知に失敗しました')
            sys.exit(1)
        else:
            logger.info('通知が完了しました')

    # 通知済みに更新
    try:
        update_transactions = []  # トランザクションリスト

        for item in notified_items:
            update_transactions.append({
                'Update': {
                    'TableName': TABLE_NAME,
                    'Key': {
                        'symbol': {'S': item['symbol']},
                        'target_price': {'S': item['target_price']}
                    },
                    'UpdateExpression': 'SET notification_sent = :notification_sent, \
                                            last_notification_date = :last_notification_date, \
                                            updated_at = :updated_at',
                    'ExpressionAttributeValues': {
                        ':notification_sent': {'BOOL': True},
                        ':last_notification_date': {'S': today_formatted},
                        ':updated_at': {'S': today_formatted}
                    }
                }
            })

        if update_transactions:
            dynamodb_client.transact_write_items(TransactItems=update_transactions)  # トランザクション実行
    except ClientError as e:
        logger.error("トランザクション処理に失敗しました。自動的に元の状態に戻されました:", e)
