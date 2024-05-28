import logging
from base64 import urlsafe_b64encode
from datetime import datetime
import json
import math
from base58 import b58decode
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from requests import PreparedRequest, Request
import urllib
from functions import get_orderly_token_price, create_session_orderly, encode_key
from config import orderly_tokens, tp_sl_percentage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OrderlyTrading(object):
    def __init__(
            self,
            wallet: dict
    ) -> None:
        self._base_url = "https://api-evm.orderly.org"
        self._account_id = wallet['account_id']
        key = b58decode(wallet['orderly_secret'])
        self._private_key = Ed25519PrivateKey.from_private_bytes(key)

    def sign_request(self, req: Request) -> PreparedRequest:
        d = datetime.utcnow()
        epoch = datetime(1970, 1, 1)
        timestamp = math.trunc((d - epoch).total_seconds() * 1_000)

        json_str = ""
        if req.json is not None:
            json_str = json.dumps(req.json)

        url = urllib.parse.urlparse(req.url)
        message = str(timestamp) + req.method + url.path + json_str
        if len(url.query) > 0:
            message += "?" + url.query

        orderly_signature = urlsafe_b64encode(
            self._private_key.sign(message.encode())
        ).decode("utf-8")
        req.headers = {
            'origin': 'https://pro.logx.trade',
            'referer': 'https://pro.logx.trade/',
            "orderly-timestamp": str(timestamp),
            "orderly-account-id": self._account_id,
            "orderly-key": encode_key(
                self._private_key.public_key().public_bytes_raw()
            ),
            "orderly-signature": orderly_signature,
        }
        if req.method == "GET" or req.method == "DELETE":
            req.headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif req.method == "POST" or req.method == "PUT":
            req.headers["Content-Type"] = "application/json"

        return req.prepare()

    def open_market_position(self, token: str, long: bool, amount_usd: int) -> bool:
        token_info = orderly_tokens[token]
        try:
            session = create_session_orderly()
            side = "BUY" if long else "SELL"
            current_token_price = get_orderly_token_price(token)
            if token in ['ARB', 'SUI']:
                token_quantity = int(amount_usd / current_token_price)
            else:
                token_quantity = round(amount_usd / float(current_token_price), token_info['decimals'])

            req = self.sign_request(
                Request(
                    "POST",
                    "%s/v1/order" % self._base_url,
                    json={
                        "symbol": f"PERP_{token}_USDC",
                        "order_type": "MARKET",
                        "order_quantity": token_quantity,
                        "side": side,
                    },
                )
            )
            res = session.send(req)
            response = json.loads(res.text)
            if response['success']:
                pos = 'Лонг' if long else 'Шорт'
                logger.info(f'Успешно открыта {pos} позиция на Orderly: {token_quantity} {token}')
                return True
            else:
                logger.error(response)
                return False
        except Exception as e:
            logger.error(f'Проблемы с открытием сделки на Orderly: {e}')
            return False

    def get_position_info(self, token: str) -> [float, any]:
        url = f"https://api-evm.orderly.network/v1/position/PERP_{token}_USDC"
        session = create_session_orderly()
        req = self.sign_request(
            Request(
                "GET",
                url,
            )
        )
        res = session.send(req)

        response = json.loads(res.text)
        average_open_price = response['data']['average_open_price']
        position_qty = abs(response['data']['position_qty'])
        if token == 'ARB':
            position_qty = int(position_qty)
        return average_open_price, position_qty

    def tp_sl(self, token: str, long: bool) -> bool:
        token_info = orderly_tokens[token]
        entry_price, position_qty = self.get_position_info(token)
        tp_sl_url = 'https://api-evm.orderly.org/v1/algo/order'
        if long:
            side = "SELL"
            lossPrice = round(entry_price - entry_price * tp_sl_percentage, token_info['tp_precision'])
            profitPrice = round(entry_price + entry_price * tp_sl_percentage, token_info['tp_precision'])
        else:
            side = "BUY"
            lossPrice = round(entry_price + entry_price * tp_sl_percentage, token_info['tp_precision'])
            profitPrice = round(entry_price - entry_price * tp_sl_percentage, token_info['tp_precision'])

        json_data = {
            'symbol': f'PERP_{token}_USDC',
            'algo_type': 'TP_SL',
            'quantity': position_qty,
            'trigger_price_type': 'MARK_PRICE',
            'order_tag': None,
            'reduce_only': True,
            'child_orders': [
                {
                    'symbol': f'PERP_{token}_USDC',
                    'algo_type': 'TAKE_PROFIT',
                    'side': side,
                    'type': 'MARKET',
                    'trigger_price': profitPrice,
                    'reduce_only': True,
                },
                {
                    'symbol': f'PERP_{token}_USDC',
                    'algo_type': 'STOP_LOSS',
                    'side': side,
                    'type': 'MARKET',
                    'trigger_price': lossPrice,
                    'reduce_only': True,
                },
            ],
        }
        session = create_session_orderly()
        try:
            req = self.sign_request(
                Request(
                    "POST",
                    tp_sl_url,
                    json=json_data,
                )
            )
            res = session.send(req)
            response = json.loads(res.text)
            if response['success']:
                logger.info(f'Позиция Orderly: {token}\n'
                            f'TP: {profitPrice}\n'
                            f'SL: {lossPrice}\n')
                return True
            else:
                logger.error(response)
                return False
        except Exception as e:
            logger.error(f'Проблема с установкой TP/SL на Orderly: {e}')
            return False

    def close_market_position(self, token: str, long: bool) -> bool:
        _, position_qty = self.get_position_info(token)
        side = "SELL" if long else "BUY"
        json_data = {
            'symbol': f'PERP_{token}_USDC',
            'order_type': 'MARKET',
            'side': side,
            'reduce_only': True,
            'order_quantity': position_qty
        }
        session = create_session_orderly()
        req = self.sign_request(
            Request(
                "POST",
                "%s/v1/order" % self._base_url,
                json=json_data,
            )
        )
        try:
            res = session.send(req)
            response = json.loads(res.text)
            if response['success']:
                pos = 'Лонг' if long else 'Шорт'
                logger.info(f'Успешно закрыта {pos} позиция на Orderly: {position_qty} {token}\n')
                return True
            else:
                logger.info(response)
                return False
        except Exception as e:
            logger.error(f'Проблема с закрытием сделки на Orderly: {e}')
            return False
