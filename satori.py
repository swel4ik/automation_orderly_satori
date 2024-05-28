import logging
import requests
import json
from config import satori_tokens, satori_leverage, tp_sl_percentage
from functions import sign_with_key, generate_unique_string

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _generate_order_id():
    filename = 'satori_orders_ids.json'
    with open(filename, 'r') as file:
        satori_ids = json.load(file)
    order_id = generate_unique_string(satori_ids['orders'])
    satori_ids['orders'].append(order_id)
    with open(filename, 'w') as file:
        json.dump(satori_ids, file, indent=4)
    return order_id


def _build_trading_data(contract_pair_id, token_amount, signature, msg, long, order_id, amount_usd):
    return {
        'contractPairId': contract_pair_id,
        'contractPositionId': 0,
        'isLong': long,
        'isMarket': True,
        'quantity': token_amount,
        'signHash': signature,
        'originMsg': msg,
        'lever': satori_leverage,
        'amount': amount_usd,
        'price': None,
        'positionType': 3,
        'matchType': 1,
        'clientOrderId': order_id,
    }


def _build_close_data(position, signature, msg, order_id):
    return {
        'contractPairId': position['contractPairId'],
        'contractPositionId': position['id'],
        'isMarket': True,
        'signHash': signature,
        'originMsg': msg,
        'clientOrderId': order_id,
        'quantity': position['quantity'],
        'isLong': position['isLong'],
        'amount': 100,
        'price': None,
    }


def _calculate_tp_sl(entry_price, long, factor):
    if long:
        lossPrice = round(entry_price - entry_price * factor, 3)
        profitPrice = round(entry_price + entry_price * factor, 3)
    else:
        lossPrice = round(entry_price + entry_price * factor, 3)
        profitPrice = round(entry_price - entry_price * factor, 3)
    return lossPrice, profitPrice


class SatoriTrading(object):
    def __init__(
            self,
            wallet: dict,
            api_token=None
    ) -> None:
        self._public_key = wallet['public_key']
        self._private_key = wallet['private_key']
        self.base_url = 'https://zksync.satori.finance/trade/'

        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US',
            'brand-exchange': 'zksync',
            'priority': 'u=1, i',
            'sec-ch-ua': wallet['sec-ch-ua'],
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': wallet['user-agent'],
        }

        if api_token:
            self.headers['authorization'] = api_token
        else:
            self.generate_api_token()

    def generate_api_token(self):
        nonce = self._get_nonce()
        try:
            signature = sign_with_key(self._private_key, nonce)
            sign_data = {'address': self._public_key, 'signature': signature}
            response = requests.post('https://zksync.satori.finance/api/auth/auth/token',
                                     headers=self.headers, json=sign_data)
            api_token = response.json()['data']
            self.headers['authorization'] = api_token
            logger.info(f'Новый токен {api_token} для Satori')
        except Exception as e:
            logger.error(f'Ошибка генерации API токена для Satori: {e}')

    def _get_nonce(self):
        json_data = {'address': self._public_key}
        try:
            response = requests.post('https://zksync.satori.finance/api/auth/auth/generateNonce',
                                     headers=self.headers, json=json_data)
            return response.json()['data']['nonce']
        except Exception as e:
            logger.error(f'Ошибка получения nonce: {e}')
            return None

    def get_timestamp(self):
        try:
            time = requests.get('https://zksync.satori.finance/api/third/info/time', headers=self.headers)
            timestamp = time.json()['data']
            return timestamp

        except Exception as e:
            logger.error(f'Ошибка получения Satori timestamp: {e}')
            return None

    def get_token_price(self, token: str):
        try:
            timestamp = self.get_timestamp()
            if timestamp is None:
                return None
            json_data = {
                'contractPairId': satori_tokens[token]['contractPairId'],
                'limit': 1,
                'period': '5MIN',
                'endTime': timestamp,
            }
            response = requests.post(
                'https://zksync.satori.finance/api/contract-quotes-provider/contract-quotes/selectKlinePillarList',
                headers=self.headers,
                json=json_data
            )
            return response.json()['data'][0]['close']
        except Exception as e:
            logger.error(f'Ошибка получения цены токена {token}: {e}')
            return None

    def check_balance(self, token: str) -> float:
        token_info = satori_tokens[token]
        self.headers['referer'] = self.base_url + token_info['url']
        response = requests.post('https://zksync.satori.finance/api/contract-provider/contract-account/overview/4',
                                 headers=self.headers).json()
        return float(response['data']['availableAmount'])

    def open_market_position(self, token: str, long: bool, amount_usd: int):
        try:
            order_id = _generate_order_id()
            token_info = satori_tokens[token]
            self.headers['referer'] = self.base_url + token_info['url']
            contract_pair_id = token_info['contractPairId']
            token_price = self.get_token_price(token)
            if token_price is None:
                return None, False
            token_amount = round(amount_usd / token_price, token_info['decimals'])
            trade_timestamp = self.get_timestamp()
            if trade_timestamp is None:
                return None, False
            trade_timestamp += 60504
            msg = f'{{"quantity":{token_amount},"address":"{self._public_key}","expireTime":"{trade_timestamp}","contractPairId":{contract_pair_id},"isClose":false,"amount":{amount_usd}}}'
            signature = sign_with_key(self._private_key, msg)
            trading_data = _build_trading_data(token_info['contractPairId'], token_amount, signature, msg, long,
                                               order_id, amount_usd)

            response = requests.post(
                'https://zksync.satori.finance/api/contract-provider/contract/order/openPosition',
                headers=self.headers,
                json=trading_data
            ).json()
            if response['msg'] == 'SUCCESS':
                pos = 'Лонг' if long else 'Шорт'
                logger.info(f'Успешно открыта {pos} позиция на Satori: {token} на {amount_usd} USDC\n'
                            f'Номер: {order_id}\n')
                return order_id, True
            else:
                logger.error(response)
                return None, False
        except Exception as e:
            logger.error(f'Ошибка открытия позиции на Satori: {e}')
            return None, False

    def close_market_position(self, token: str, order_id: str):
        try:
            position = self._get_position(token)
            if not position:
                return False
            close_timestamp = self.get_timestamp() + 60504
            msg = f'{{"quantity":{position["quantity"]},"address":"{self._public_key}","expireTime":"{close_timestamp}","contractPairId":{position["contractPairId"]},"isClose":true,"amount":100}}'
            signature = sign_with_key(self._private_key, msg)
            close_data = _build_close_data(position, signature, msg, order_id)
            response = requests.post('https://zksync.satori.finance/api/contract-provider/contract/order/closePosition',
                                     headers=self.headers, json=close_data).json()
            if response['msg'] == 'SUCCESS':
                pos = 'Лонг' if position['isLong'] else 'Шорт'
                logger.info(f'Успешно закрыта {pos} позиция на Satori: {token}\n'
                            f'Номер: {order_id}\n')
                return True
            else:
                logger.error("Позиция на Satori не была закрыта")
                logger.error(response)
                return False
        except Exception as e:
            logger.error(f'Ошибка закрытия рыночной позиции на Satori: {e}')
            return False

    def _get_position(self, token: str):
        token_info = satori_tokens[token]
        self.headers['referer'] = self.base_url + token_info['url']
        position_data = {'pageNo': 1, 'pageSize': 10}
        response = \
            requests.post('https://zksync.satori.finance/api/contract-provider/contract/selectContractPositionList',
                          headers=self.headers, json=position_data).json()['data']
        return response['records'][0]

    def tp_sl(self, token: str, long: bool):
        try:
            position = self._get_position(token)
            entry_price = float(position['openingPrice'])
            lossPrice, profitPrice = _calculate_tp_sl(entry_price, long, tp_sl_percentage)
            json_data = {
                'id': position['id'],
                'lossPrice': lossPrice,
                'lossType': 2,
                'profitPrice': profitPrice,
                'profitType': 2,
            }
            response = requests.post('https://zksync.satori.finance/api/contract-provider/contract/updateStopConfig',
                                     headers=self.headers, json=json_data).json()
            if response['msg'] == 'SUCCESS':
                logger.info(f'Позиция Satori: {token}\n'
                            f'Ордер: {position["id"]}\n'
                            f'TP: {profitPrice}\n'
                            f'SL: {lossPrice}\n')
                return True
            else:
                logger.error(response)
                return False
        except Exception as e:
            logger.error(f'Ошибка установки TP/SL для токена {token}: {e}')
            return False
