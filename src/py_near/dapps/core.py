NEAR = 1_000_000_000_000_000_000_000_000

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py_near.account import Account


class DappClient:
    """
    Base client class for dApp interactions.

    Provides a common interface for dApp-specific clients that interact with
    smart contracts on the NEAR blockchain.
    """

    def __init__(self, account: "Account"):
        """
        Initialize dApp client.

        Args:
            account: Account instance for interacting with the blockchain
        """
        self._account = account

