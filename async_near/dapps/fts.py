from dataclasses import dataclass


@dataclass
class FtModel:
    contract_id: str
    decimal: int


class FTS:
    USDC = FtModel("dac17f958d2ee523a2206206994597c13d831ec7.factory.bridge.near", 6)
    DAI = FtModel("6b175474e89094c44da98b954eedeac495271d0f.factory.bridge.near", 6)
    USDT = FtModel("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.factory.bridge.near", 6)
    wNEAR = FtModel("wrap.near", 24)
    LINEAR = FtModel("linear-protocol.near", 24)
    ETH = FtModel("aurora", 18)
    WBTC = FtModel("2260fac5e5542a773aa44fbcfedf7c193bc2c599.factory.bridge.near", 8)
    stNEAR = FtModel("meta-pool.near", 24)
    META = FtModel("meta-token.near", 24)
    AURORA = FtModel("aaaaaa20d9e0e2461697782ef11675f668207961.factory.bridge.near", 18)
    stHERE = FtModel("storage.herewallet.near", 24)
