orderly_tokens = {
    'ETH': {
        'decimals': 4,
        'tp_precision': 2
    },
    'OP': {
        'decimals': 1,
        'tp_precision': 3
    },
    'ARB': {
        'decimals': 0,
        'tp_precision': 3
    },
    'SOL': {
        'decimals': 2,
        'tp_precision': 3
    },
    'APT': {
        'decimals': 1,
        'tp_precision': 3
    },
    'SUI': {
        'decimals': 0,
        'tp_precision': 3
    },
    'BNB': {
        'decimals': 3,
        'tp_precision': 2
    },
    'STRK': {
        'decimals': 1,
        'tp_precision': 3
    }
}

satori_tokens = {
    'ETH': {
        'url': 'ETH-USD',
        'contractPairId': 1,
        'decimals': 3
    },
    'OP': {
        'url': 'OP-USD',
        'contractPairId': 13,
        'decimals': 1
    },
    'ARB': {
        'url': 'ARB-USD',
        'contractPairId': 9,
        'decimals': 1
    },
    'SOL': {
        'url': 'SOL-USD',
        'contractPairId': 6,
        'decimals': 2
    }
}

tokens = ['ARB', 'OP']
tokens_probs = [0.5, 0.5]
trade_amount_usd = [30, 55]
tp_sl_time = [10, 30]
position_time = [30, 60]
trade_pause_time = [140, 270]
needed_vol = 30000
satori_leverage = 20
tp_sl_percentage = 0.032



