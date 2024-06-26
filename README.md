# Automation Trading Bot On Satori-LogX
## Логика:
1. Открывает маркет ордер на Satori, затем сразу же открывает хедж ордер на LogX
2. Через кастомное время выставляет TP/SL на обеих площадках
3. Закрывает позиции маркет ордерами через кастомное время 
## Настройка:
1. В `config.py` нужно указать:
- **tokens** список токенов, которые будут торговаться
- **tokens_probs** вероятности для токенов (т.е. с какой вероятностью откроется позиция на определенный токен)
- **trade_amount_usd** нижняя и верхняя граница размера позиции в USD
- **tp_sl_time** время в секундах, перед установкой tp/sl
- **position_time** время между открытием/закрытием позиций в секундах
- **trade_pause_time** время между трейдами
- **needed_vol** сколько нужно набрать объема в USD
- **satori_leverage** размера плеча на Satori
2. В `wallets.py` указать:
- **account_id**: взять с LogX
- **orderly_api**: взять с LogX
- **orderly_secret**: взять с LogX
- **public_key**: адрес кошелька
- **private_key**: приватный ключ
- **user-agent**
- **sec-ch-ua**
## Запуск:
1. `pip install -r requirements.txt`
2. `python main.py`
