from pynear.dapps.ft.exceptions import NotRegisteredError, NotEnoughBalance
from pynear.exceptions.exceptions import FunctionCallError

from pynear.dapps.core import DappClient, NEAR
from pynear.dapps.ft.models import FtTokenMetadata
from pynear.dapps.fts import FtModel


class FT(DappClient):
    async def get_ft_balance(self, ft: FtModel, account_id: str) -> float:
        return (
            await self._account.view_function(
                ft.contract_id,
                "ft_balance_of",
                {"account_id": account_id},
            )
        ).result // 10**ft.decimal

    async def get_metadata(self, ft: FtModel) -> FtTokenMetadata:
        return FtTokenMetadata(
            **(
                await self._account.view_function(
                    ft.contract_id,
                    "ft_metadata",
                    {},
                )
            ).result
        )

    async def transfer(self, ft: FtModel, receiver_id: str, amount: float, memo: str = ""):
        try:
            return await self._account.function_call(
                ft.contract_id,
                "ft_transfer",
                {
                    "receiver_id": receiver_id,
                    "amount": str(int(amount * 10**ft.decimal)),
                    "msg": memo,
                },
                amount=1,
            )
        except FunctionCallError as e:
            if "The account is not registered" in e.error["ExecutionError"]:
                raise NotRegisteredError(e)
            if "The account doesn't have enough balance" in e.error["ExecutionError"]:
                raise NotEnoughBalance(e)
            raise e

    async def transfer_call(self, ft: FtModel, receiver_id: str, amount: float, memo: str = ""):
        return await self._account.function_call(
            ft.contract_id,
            "ft_transfer_call",
            {
                "receiver_id": receiver_id,
                "amount": str(int(amount * 10**ft.decimal)),
                "msg": memo,
            },
            amount=1,
        )

    async def storage_balance_of(self, contract_id, near_account_id: str):
        return (
            await self._account.view_function(
                contract_id,
                "storage_balance_of",
                {"account_id": near_account_id},
            )
        ).result

    async def storage_deposit(self, ft: FtModel, near_account_id: str, amount: int = NEAR // 100):
        return await self._account.function_call(
            ft.contract_id,
            "storage_deposit",
            {"account_id": near_account_id},
            amount=amount,
        )
