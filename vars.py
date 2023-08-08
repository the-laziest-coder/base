import json


INVOLVED_CHAINS = ['Ethereum', 'Base']

SCANS = {
    'Ethereum': 'https://etherscan.io',
    'Optimism': 'https://optimistic.etherscan.io',
    'BSC': 'https://bscscan.com',
    'Gnosis': 'https://gnosisscan.io',
    'Polygon': 'https://polygonscan.com',
    'Fantom': 'https://ftmscan.com',
    'Arbitrum': 'https://arbiscan.io',
    'Avalanche': 'https://snowtrace.io',
    'zkSync': 'https://explorer.zksync.io',
    'zkEVM': 'https://zkevm.polygonscan.com',
    'Zora': 'https://explorer.zora.energy',
    'Base': 'https://basescan.org',
}

CHAIN_IDS = {
    'Ethereum': 1,
    'Optimism': 10,
    'BSC': 56,
    'Gnosis': 100,
    'Polygon': 137,
    'Fantom': 250,
    'Arbitrum': 42161,
    'Avalanche': 43114,
    'zkSync': 324,
    'zkEVM': 1101,
    'Zora': 7777777,
    'Base': 8453,
}

CHAIN_NAMES = {
    1: 'Ethereum',
    10: 'Optimism',
    56: 'BSC',
    100: 'Gnosis',
    137: 'Polygon',
    250: 'Fantom',
    42161: 'Arbitrum',
    43114: 'Avalanche',
    1313161554: 'Aurora',
    324: 'zkSync',
    1101: 'zkEVM',
    7777777: 'Zora',
    8453: 'Base',
}

EIP1559_CHAINS = ['Ethereum', 'Base']

NATIVE_TOKEN_ADDRESS = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'

NATIVE_DECIMALS = 18

BASE_BRIDGE_GAS_LIMIT = 100000
BASE_MINT_FUN_BRIDGE_GAS_LIMIT = 222000
BASE_ONCHAIN_SUMMER_BRIDGE_GAS_LIMIT = 200000

MINT_FUN_BRIDGE_PASS_ADDRESS = '0x00008453E27e8e88F305F13CF27c30D724fDd055'

ONCHAIN_SUMMER_BRIDGE_ADDRESS = '0x3154Cf16ccdb4C6d922629664174b904d80F2C35'
ONCHAIN_SUMMER_BRIDGE_ABI = json.load(open('abi/onchain_summer_bridge.json'))

BASE_BRIDGE_ADDRESS = '0x49048044D57e1C92A77f79988d21Fa8fAF74E97e'
BASE_BRIDGE_ABI = json.load(open('abi/base_bridge.json'))

BASE_FOR_BUILDERS_ADDRESS = '0x1FC10ef15E041C5D3C54042e52EB0C54CB9b710c'
BASE_FOR_BUILDERS_ABI = json.load(open('abi/base_for_builders.json'))

BASE_NFT_ABI = json.load(open('abi/nft.json'))
