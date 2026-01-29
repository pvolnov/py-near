"""Constants for omni_balance operations."""
from enum import Enum

# Standard tokens for intermediate swaps
USDT_TOKEN = "usdt.tether-token.near"
WRAP_NEAR = "wrap.near"

# Mapping of assets to NEAR contracts
NEAR_CONTRACT_BY_ASSET: dict[str, str] = dict()

# Solver Bus API URL
SOLVER_BUS_URL = "https://solver-relay-v2.chaindefuser.com/rpc"
SOLVER_BUS_WSS = "wss://solver-relay-v2.chaindefuser.com/ws"
# Headers for Solver API requests
INTENTS_HEADERS = {"Content-Type": "application/json"}

# Intents contract address
INTENTS_CONTRACT = "intents.near"

# Maximum gas for transactions
MAX_GAS = 300_000_000_000_000

class OmniToken(str, Enum):
    USDT = "nep141:usdt.tether-token.near"
    WRAP_NEAR = "nep141:wrap.near"
    GNK = "nep245:v2_1.omni.hot.tg:4444119_wyixUKCL"

