from web3 import Web3
from eth_account.messages import encode_defunct
import random
import string
import requests
from base58 import b58encode

web3 = Web3()


def sign_with_key(private_key, message):
    account = web3.eth.account.from_key(private_key)
    signature = account.sign_message(encode_defunct(text=message)).signature.hex()

    return signature


def generate_random_string(length=21):
    characters = string.ascii_letters + string.digits + "-_"
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def generate_unique_string(existing_list, length=21):
    while True:
        new_string = generate_random_string(length)
        if new_string not in existing_list:
            return new_string


def get_orderly_token_price(token: str):
    url = f"https://api-evm.orderly.network/v1/public/futures/PERP_{token}_USDC"
    response_ = requests.request("GET", url).json()['data']['index_price']
    return response_


def create_session_orderly():
    session = requests.Session()
    return session


def encode_key(key: bytes):
    return "ed25519:%s" % b58encode(key).decode("utf-8")


