from py_near.dapps.core import DappClient
from py_near.dapps.keypom.models import CreateDropModel

_KEYPOM_CONTRACT_ID = "keypom.near"


class KeyPom(DappClient):
    """
    Client for interacting with KeyPom linkdrop contract.

    KeyPom allows sending NEAR and fungible tokens via linkdrops and receiving
    FT/NFT/NEAR from other linkdrops. This client provides methods for creating
    drops and claiming linkdrops.
    """

    def __init__(self, account, contract_id=_KEYPOM_CONTRACT_ID):
        """
        Initialize KeyPom client.

        Args:
            account: Account instance for interacting with the contract
            contract_id: KeyPom contract ID (default: "keypom.near")

        Raises:
            ValueError: If chain_id is not "mainnet" (only mainnet is supported)
        """
        if account.chain_id != "mainnet":
            raise ValueError("Only mainnet is supported")
        super().__init__(account)
        self.contract_id = contract_id

    async def create_drop(
        self,
        drop: CreateDropModel,
    ) -> str:
        """
        Create a new linkdrop.

        Args:
            drop: CreateDropModel containing drop configuration

        Returns:
            Drop ID string
        """
        res = await self._account.view_function(
            self.contract_id,
            "create_drop",
            drop.dict(),
        )
        return res.result

    async def claim(self, account_id: str, password: str):
        """
        Claim a linkdrop.

        Args:
            account_id: Account ID that will receive the linkdrop
            password: Linkdrop password/secret

        Returns:
            ViewFunctionResult from the claim operation
        """
        return await self._account.view_function(
            self.contract_id,
            "claim",
            {"account_id": account_id, password: password},
        )
