import logging
from satori import SatoriTrading
from orderly import OrderlyTrading
from wallets import wallets
from config import tokens, trade_amount_usd, tokens_probs, tp_sl_time, position_time, trade_pause_time, needed_vol, \
    satori_leverage
from logic import trade_cycle


wallet = 'main'

logging.info(f'Текущий аккаунт: {wallet}')

if __name__ == "__main__":
    orderly_bot = OrderlyTrading(wallet=wallets[wallet])
    satori_bot = SatoriTrading(wallet=wallets[wallet])
    trade_cycle(orderly_bot, satori_bot, tokens, tokens_probs, trade_amount_usd, needed_vol, satori_leverage, tp_sl_time, position_time, trade_pause_time)