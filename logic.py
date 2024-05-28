import random
import sys
import time
import logging

logger = logging.getLogger(__name__)


def check_satori_balance(bot, token, amount_usd, leverage):
    balance = bot.check_balance(token)
    if balance * leverage < amount_usd:
        logger.info("Недостаточно баланса на Satori")
        sys.exit()
    return balance


def open_positions(satori_bot, orderly_bot, token, satori_pos, orderly_pos, amount_usd):
    satori_order_id, satori_status = satori_bot.open_market_position(token=token, long=satori_pos,
                                                                     amount_usd=amount_usd)
    if not satori_status:
        sys.exit()

    orderly_status = orderly_bot.open_market_position(token=token, long=orderly_pos, amount_usd=amount_usd)
    if not orderly_status:
        satori_close_status = satori_bot.close_market_position(token, satori_order_id)
        if not satori_close_status:
            sys.exit()
    return satori_order_id, satori_status, orderly_status


def set_tp_sl(satori_bot, orderly_bot, token, satori_pos, orderly_pos):
    orderly_tp_sl_status = orderly_bot.tp_sl(token, orderly_pos)
    satori_tp_sl_status = satori_bot.tp_sl(token, satori_pos)
    if not orderly_tp_sl_status or not satori_tp_sl_status:
        satori_close_status = satori_bot.close_market_position(token, satori_pos)
        orderly_close_status = orderly_bot.close_market_position(token, orderly_pos)
        if not satori_close_status or not orderly_close_status:
            logger.error("Не удалось закрыть одну из позиций")
            sys.exit()
        else:
            logger.info("Позиции закрыты из-за проблемы с TP/SL")
            sys.exit()


def close_positions(satori_bot, orderly_bot, token, satori_order_id, orderly_pos):
    satori_close_status = satori_bot.close_market_position(token, satori_order_id)
    orderly_close_status = orderly_bot.close_market_position(token, orderly_pos)
    if not satori_close_status or not orderly_close_status:
        sys.exit()


def trade_cycle(orderly_bot, satori_bot, tokens, tokens_probs, trade_amount_usd, needed_vol, satori_leverage,
                tp_sl_time, position_time, trade_pause_time):
    vol = 0
    while vol < needed_vol:
        token = random.choices(tokens, tokens_probs, k=1)[0]
        amount_usd = random.randint(trade_amount_usd[0], trade_amount_usd[1])
        satori_pos = random.choice([True, False])
        orderly_pos = not satori_pos

        check_satori_balance(satori_bot, token, amount_usd, satori_leverage)

        satori_order_id, satori_status, orderly_status = open_positions(
            satori_bot, orderly_bot, token, satori_pos, orderly_pos, amount_usd)

        if not orderly_status:
            sys.exit()

        vol += amount_usd

        tp_sl_delay = random.randint(tp_sl_time[0], tp_sl_time[1])
        logger.info(f'\nЖдем {tp_sl_delay} сек перед установкой TP/SL\n')
        time.sleep(tp_sl_delay)

        set_tp_sl(satori_bot, orderly_bot, token, satori_pos, orderly_pos)

        position_delay = random.randint(position_time[0], position_time[1])
        logger.info(f'\nЖдем {position_delay / 60} минут перед закрытием позиций\n')
        time.sleep(position_delay)

        close_positions(satori_bot, orderly_bot, token, satori_order_id, orderly_pos)

        vol += amount_usd
        pause = random.randint(trade_pause_time[0], trade_pause_time[1])
        logger.info(f'\nЖдем {pause / 60} минут перед следующей сделкой\nТекущий объем: {vol}/{needed_vol}\n')
        time.sleep(pause)
