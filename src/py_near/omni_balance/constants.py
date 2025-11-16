"""Constants for omni_balance operations."""

# Standard tokens for intermediate swaps
USDT_TOKEN = "usdt.tether-token.near"
WRAP_NEAR = "wrap.near"

# Mapping of assets to NEAR contracts
NEAR_CONTRACT_BY_ASSET: dict[str, str] = dict()

# Solver Bus API URL
SOLVER_BUS_URL = "https://solver-relay-v2.chaindefuser.com/rpc"

# Headers for Solver API requests
INTENTS_HEADERS = {"Content-Type": "application/json"}

# Intents contract address
INTENTS_CONTRACT = "intents.near"

# Maximum gas for transactions
MAX_GAS = 300_000_000_000_000

