import sys
import csv
import random
import time
import colorama
import web3.exceptions

from termcolor import cprint
from enum import Enum
from pathlib import Path
from datetime import datetime
from loguru import logger
from eth_account.account import Account
from eth_account.messages import encode_defunct

from utils import *
from config import *
from vars import *


colorama.init()
logger.remove()
logger.add(sys.stdout, level='INFO')

date_path = datetime.now().strftime('%d-%m-%Y-%H-%M-%S')
results_path = 'results/' + date_path
logs_root = 'logs/'
logs_path = logs_root + date_path
Path(results_path).mkdir(parents=True, exist_ok=True)
Path(logs_path).mkdir(parents=True, exist_ok=True)


def decimal_to_int(d, n):
    return int(d * (10 ** n))


def int_to_decimal(i, n):
    return i / (10 ** n)


def readable_amount_int(i, n, d=2):
    return round(int_to_decimal(i, n), d)


def wait_next_tx(x=1.0):
    time.sleep(random.uniform(NEXT_TX_MIN_WAIT_TIME, NEXT_TX_MAX_WAIT_TIME) * x)


def _delay(r, *args, **kwargs):
    time.sleep(random.uniform(1, 2))


class RunnerException(Exception):

    def __init__(self, message, caused=None):
        super().__init__()
        self.message = message
        self.caused = caused

    def __str__(self):
        if self.caused:
            return self.message + ": " + str(self.caused)
        return self.message


class PendingException(Exception):

    def __init__(self, chain, tx_hash, action):
        super().__init__()
        self.chain = chain
        self.tx_hash = tx_hash
        self.action = action

    def __str__(self):
        return f'{self.action}, chain = {self.chain}, tx_hash = {self.tx_hash.hex()}'

    def get_tx_hash(self):
        return self.tx_hash.hex()


def runner_func(msg):
    def decorator(func):
        @retry(tries=MAX_TRIES, delay=1.5, backoff=2, jitter=(0, 1), exceptions=RunnerException)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (PendingException, InsufficientFundsException):
                raise
            except Exception as e:
                raise RunnerException(msg, e)

        return wrapper

    return decorator


class Status(Enum):
    ALREADY = 1
    PENDING = 2
    SUCCESS = 3
    FAILED = 4


class Runner:

    def __init__(self, private_key, proxy):
        if proxy is not None and len(proxy) > 4 and proxy[:4] != 'http':
            proxy = 'http://' + proxy
        self.proxy = proxy

        self.w3s = {chain: get_w3(chain, proxy=self.proxy) for chain in INVOLVED_CHAINS}

        self.private_key = private_key
        self.address = Account().from_key(private_key).address

    def w3(self, chain):
        return self.w3s[chain]

    def tx_verification(self, chain, tx_hash, action=None):
        action_print = action + ' - ' if action else ''
        logger.info(f'{action_print}Tx was sent')
        try:
            transaction_data = self.w3(chain).eth.wait_for_transaction_receipt(tx_hash)
            status = transaction_data.get('status')
            if status is not None and status == 1:
                logger.info(f'{action_print}Successful tx: {SCANS[chain]}/tx/{tx_hash.hex()}')
            else:
                raise RunnerException(f'{action_print}Tx status = {status}, chain = {chain}, tx_hash = {tx_hash.hex()}')
        except web3.exceptions.TimeExhausted:
            logger.info(f'{action_print} Tx in pending: {SCANS[chain]}/tx/{tx_hash.hex()}')
            raise PendingException(chain, tx_hash, action_print[:-3])

    def get_native_balance(self, chain):
        return self.w3(chain).eth.get_balance(self.address)

    def build_and_send_tx(self, w3, func, action, value=0):
        return build_and_send_tx(w3, self.address, self.private_key, func, value, self.tx_verification, action)

    @classmethod
    def wait_for_eth_gas_price(cls, w3):
        t = 0
        while w3.eth.gas_price > Web3.to_wei(MAX_ETH_GAS_PRICE, 'gwei'):
            gas_price = int_to_decimal(w3.eth.gas_price, 9)
            gas_price = round(gas_price, 2)
            logger.info(f'Gas price is too high - {gas_price}. Waiting for {WAIT_GAS_TIME}s')
            t += WAIT_GAS_TIME
            if t >= TOTAL_WAIT_GAS_TIME:
                break
            time.sleep(WAIT_GAS_TIME)

        if w3.eth.gas_price > Web3.to_wei(MAX_ETH_GAS_PRICE, 'gwei'):
            raise RunnerException('Gas price is too high')

    def wait_for_bridge(self, init_balance):
        t = 0
        while init_balance >= self.get_native_balance('Base') and t < BRIDGE_WAIT_TIME:
            t += 20
            logger.info('Assets not bridged')
            time.sleep(20)

        if init_balance >= self.get_native_balance('Base'):
            raise RunnerException('Bridge takes too long')

        logger.info('Assets bridged successfully')

    @runner_func('Onchain Summer Bridge')
    def onchain_summer_bridge(self):
        w3 = self.w3('Ethereum')

        contract = w3.eth.contract(ONCHAIN_SUMMER_BRIDGE_ADDRESS, abi=ONCHAIN_SUMMER_BRIDGE_ABI)

        amount = random.uniform(BRIDGE_AMOUNT[0], BRIDGE_AMOUNT[1])
        amount = round(amount, random.randint(4, 6))
        value = Web3.to_wei(amount, 'ether')

        self.wait_for_eth_gas_price(w3)

        self.build_and_send_tx(
            w3,
            contract.functions.depositETH(BASE_ONCHAIN_SUMMER_BRIDGE_GAS_LIMIT, b''),
            value=value,
            action='Onchain Summer Bridge'
        )

        return Status.SUCCESS

    @runner_func('Bridge')
    def official_bridge(self):
        w3 = self.w3('Ethereum')

        contract = w3.eth.contract(BASE_BRIDGE_ADDRESS, abi=BASE_BRIDGE_ABI)

        if BRIDGE_WITH_MINT_FUN:
            recipient = MINT_FUN_BRIDGE_PASS_ADDRESS
            gas_limit = BASE_MINT_FUN_BRIDGE_GAS_LIMIT
            data = '0x8c874ebd0021fb3f'
            value = Web3.to_wei(0.001, 'ether')
            action = 'Bridge with mint.fun'
        else:
            recipient = self.address
            gas_limit = BASE_BRIDGE_GAS_LIMIT
            data = '0x01'
            amount = random.uniform(BRIDGE_AMOUNT[0], BRIDGE_AMOUNT[1])
            amount = round(amount, random.randint(4, 6))
            value = Web3.to_wei(amount, 'ether')
            action = 'Official bridge'

        self.wait_for_eth_gas_price(w3)

        self.build_and_send_tx(
            w3,
            contract.functions.depositTransaction(recipient, value, gas_limit, False, to_bytes(data)),
            value=value,
            action=action
        )

        return Status.SUCCESS

    def bridge(self):
        return self.onchain_summer_bridge() if BRIDGE_WITH_ONCHAIN_SUMMER else self.official_bridge()

    @runner_func('Mint Base if for builders')
    def mint_base_for_builders(self, w3):
        contract = w3.eth.contract(BASE_FOR_BUILDERS_ADDRESS, abi=BASE_FOR_BUILDERS_ABI)

        if contract.functions.balanceOf(self.address).call() > 0:
            return Status.ALREADY

        message = encode_defunct(text='all your base are belong to you.')
        signature = w3.eth.account.sign_message(message, private_key=self.private_key).signature.hex()

        self.build_and_send_tx(
            w3,
            contract.functions.mint(to_bytes(signature)),
            action='Mint Base is for builders',
        )

        return Status.SUCCESS

    @runner_func('Mint NFT')
    def mint_nft(self, w3, nft_address):
        contract = w3.eth.contract(nft_address, abi=BASE_NFT_ABI)

        if contract.functions.balanceOf(self.address).call() > 0:
            return Status.ALREADY

        args = (self.address, 1, NATIVE_TOKEN_ADDRESS, 0, ([], 2 ** 256 - 1, 0, NATIVE_TOKEN_ADDRESS), b'')

        self.build_and_send_tx(
            w3,
            contract.functions.claim(*args),
            action='Mint NFT',
        )

        return Status.SUCCESS

    def _mint(self, nft_address):
        w3 = self.w3('Base')

        def mint_func():
            if nft_address == BASE_FOR_BUILDERS_ADDRESS:
                return self.mint_base_for_builders(w3)
            else:
                return self.mint_nft(w3, nft_address)

        try:
            return mint_func()
        except InsufficientFundsException:
            logger.info(f'Insufficient funds on Base. Let\'s bridge')
            init_balance = self.get_native_balance('Base')
            self.bridge()
            self.wait_for_bridge(init_balance)
            wait_next_tx()
            return mint_func()

    def mint(self, nft_address):
        try:
            return self._mint(nft_address)
        except PendingException:
            return Status.PENDING


def get_nft_name(w3, nft_address):
    return w3.eth.contract(nft_address, abi=BASE_NFT_ABI).functions.name().call()


def wait_next_run(idx, runs_count):
    wait = random.randint(
        int(NEXT_ADDRESS_MIN_WAIT_TIME * 60),
        int(NEXT_ADDRESS_MAX_WAIT_TIME * 60)
    )

    done_msg = f'Done: {idx}/{runs_count}'
    waiting_msg = 'Waiting for next run for {:.2f} minutes'.format(wait / 60)

    cprint('\n#########################################\n#', 'cyan', end='')
    cprint(done_msg.center(39), 'magenta', end='')
    cprint('#\n#########################################', 'cyan', end='')

    cprint('\n# ', 'cyan', end='')
    cprint(waiting_msg, 'magenta', end='')
    cprint(' #\n#########################################\n', 'cyan')

    time.sleep(wait)


def main():
    random.seed(int(datetime.now().timestamp()))

    if BRIDGE_WITH_MINT_FUN and BRIDGE_WITH_ONCHAIN_SUMMER:
        logger.error("Can\'t bridge with mint fun and with onchain summer. Choose only one")
        exit(0)

    with open('files/wallets.txt', 'r', encoding='utf-8') as file:
        wallets = file.read().splitlines()
    with open('files/proxies.txt', 'r', encoding='utf-8') as file:
        proxies = file.read().splitlines()

    if len(proxies) == 0:
        proxies = [None] * len(wallets)
    if len(proxies) != len(wallets):
        cprint('Proxies count doesn\'t match wallets count. Add proxies or leave proxies file empty', 'red')
        return

    queue = list(zip(wallets, proxies))

    idx, runs_count = 0, len(queue)

    stats = {}
    base_w3 = get_w3('Base')

    mint_addresses = [Web3.to_checksum_address(addr) for addr in MINT_ADDRESSES]

    try:
        mint_names = {addr: get_nft_name(base_w3, addr) for addr in mint_addresses}
    except Exception as e:
        logger.error(f'Can\'t get nft names: {str(e)}')
        exit(0)

    for wallet, proxy in queue:
        if wallet.find(';') == -1:
            key = wallet
        else:
            key = wallet.split(';')[1]

        address = Account().from_key(key).address
        stats[address] = set()

    random.shuffle(queue)

    while len(queue) != 0:

        if idx != 0:
            wait_next_run(idx, runs_count)

        account = queue.pop(0)

        wallet, proxy = account

        if wallet.find(';') == -1:
            key = wallet
        else:
            key = wallet.split(';')[1]

        address = Account().from_key(key).address
        logger.info(address)

        try:
            runner = Runner(key, proxy)
        except Exception as e:
            logger.error(f'Failed to init: {str(e)}', color='red')
            continue

        random.shuffle(mint_addresses)

        for nft_address in mint_addresses:
            name = mint_names[nft_address]
            logger.info(f'{name}: Starting mint')
            try:
                status = runner.mint(nft_address)
                if status == Status.SUCCESS:
                    logger.info(f'{name}: Successfully minted')
                elif status == Status.ALREADY:
                    logger.info(f'{name}: Was already minted')
                elif status == Status.PENDING:
                    logger.info(f'{name}: Mint tx in pending')
                stats[address].add(name)
                wait_next_tx()
            except Exception as e:
                logger.error(f'{name}: Mint failed - {str(e)}')

        with open(f'{results_path}/report.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            header = ['Address'] + [mint_names[name] for name in mint_names]
            csv_data = [header]
            for addr in stats:
                row = [addr]
                for name in mint_names:
                    row.append(mint_names[name] in stats[addr])
                csv_data.append(row)
            writer.writerows(csv_data)

        idx += 1

    cprint('\n#########################################\n#', 'cyan', end='')
    cprint(f'Finished'.center(39), 'magenta', end='')
    cprint('#\n#########################################', 'cyan')


if __name__ == '__main__':
    cprint('###########################################################', 'cyan')
    cprint('#################', 'cyan', end='')
    cprint(' https://t.me/timfamecode ', 'magenta', end='')
    cprint('################', 'cyan')
    cprint('#################', 'cyan', end='')
    cprint(' https://t.me/timfamecode ', 'magenta', end='')
    cprint('################', 'cyan')
    cprint('#################', 'cyan', end='')
    cprint(' https://t.me/timfamecode ', 'magenta', end='')
    cprint('################', 'cyan')
    cprint('###########################################################\n', 'cyan')

    main()
