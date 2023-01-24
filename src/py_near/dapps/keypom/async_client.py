from py_near.dapps.core import DappClient
from py_near.dapps.keypom.models import CreateDropModel

_KEYPOM_CONTRACT_ID = "keypom.near"


class KeyPom(DappClient):
    """
    Client to keypom.near contract
    With this contract you can send NEAR and fungible tokens to linkdrop and receive FT/NFT/NEAR from other linkdrops
    """

    def __init__(self, account, contract_id=_KEYPOM_CONTRACT_ID):
        """

        :param account:
        :param contract_id: keypom contract id
        :param network: "mainnet" or "testnet"
        """
        if account.chain_id != "mainnet":
            raise ValueError("Only mainnet is supported")
        super().__init__(account)
        self.contract_id = contract_id

    def create_drop(
        self,
        drop: CreateDropModel,
    ) -> str:
        """

        :param drop: CreateDropModel
        :return: drop id
        """
        res = await self._account.view_function(
            self.contract_id,
            "create_drop",
            drop.dict(),
        )
        return res.result

    async def claim(self, account_id: str, password: str):
        """

        :param account_id: linkdrop receiver account id
        :param password: linkdrop password
        :return:
        """
        return await self._account.view_function(
            self.contract_id,
            "claim",
            {"account_id": account_id, password: password},
        )
