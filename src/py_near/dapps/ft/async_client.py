from typing import Union

from py_near.dapps.ft.exceptions import NotRegisteredError, NotEnoughBalance
from py_near.exceptions.exceptions import FunctionCallError

from py_near.dapps.core import DappClient, NEAR
from py_near.dapps.ft.models import FtTokenMetadata
from py_near.dapps.fts import FtModel
from typing import Optional


class FT(DappClient):
    async def get_ft_balance(
        self, ft: FtModel, account_id: Optional[str] = None
    ) -> float:
        """
        Get fungible token balance
        :param ft: fungible token model FT.USDC
        :param account_id: account id
        :return: amount // 10**ft.decimal
        """
        if not account_id:
            account_id = self._account.account_id
        return (
            await self.get_ft_raw_balance(ft.contract_id, account_id) / 10**ft.decimal
        )

    async def get_ft_raw_balance(
        self, contract_id: str, account_id: Optional[str] = None
    ) -> int:
        """
        Get fungible token raw balance
        :param contract_id: fungible token contract adress
        :param account_id: account id
        :return: amount
        """
        if not account_id:
            account_id = self._account.account_id
        return int(
            (
                await self._account.view_function(
                    contract_id,
                    "ft_balance_of",
                    {"account_id": account_id},
                )
            ).result
            or 0
        )

    async def get_metadata(self, ft: Union[FtModel, str]) -> FtTokenMetadata:
        """
        Get fungible token metadata
        :param ft: fungible token model FT.USDC
        :return: FtTokenMetadata
        """
        if isinstance(ft, FtModel):
            contract_id = ft.contract_id
        else:
            contract_id = ft
        return FtTokenMetadata(
            **(
                await self._account.view_function(
                    contract_id,
                    "ft_metadata",
                    {},
                )
            ).result
        )

    async def transfer(
        self,
        ft: FtModel,
        receiver_id: str,
        amount: float,
        memo: str = "",
        force_register: bool = False,
        nowait: bool = False,
    ):
        """
        Transfer fungible token to account

        :param ft: fungible token model FT.USDC
        :param receiver_id: receiver account id
        :param amount: float amount to transfer. 1 for 1 USDC
        :param memo: comment
        :param force_register: use storage_deposit() if account is not registered
        :return: transaction hash ot TransactionResult
        """
        if (
            force_register
            and await self.storage_balance_of(ft, receiver_id) < NEAR // 500
        ):
            await self.storage_deposit(ft, receiver_id)
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
                nowait=nowait,
            )
        except FunctionCallError as e:
            if "The account is not registered" in e.error["ExecutionError"]:
                raise NotRegisteredError(
                    "The receiver is not registered, user .storage_deposit() method to register it"
                )
            if "The account doesn't have enough balance" in e.error["ExecutionError"]:
                raise NotEnoughBalance(e)
            raise e

    async def transfer_call(
        self,
        ft: FtModel,
        receiver_id: str,
        amount: float,
        memo: str = "",
        force_register: bool = False,
        nowait: bool = False,
    ):
        """
        Transfer fungible token to account and call ft_on_transfer() method in receiver contract

        :param ft: fungible token model FT.USDC
        :param receiver_id: receiver account id
        :param amount: float amount to transfer. 1 for 1 USDC
        :param memo: comment
        :param force_register: use storage_deposit() if account is not registered
        :param nowait if True, method will return before transaction is confirmed
        :return: transaction hash ot TransactionResult
        """
        if (
            force_register
            and await self.storage_balance_of(ft, receiver_id) < NEAR // 500
        ):
            await self.storage_deposit(ft, receiver_id)
        return await self._account.function_call(
            ft.contract_id,
            "ft_transfer_call",
            {
                "receiver_id": receiver_id,
                "amount": str(int(amount * 10**ft.decimal)),
                "msg": memo,
            },
            amount=1,
            nowait=nowait,
        )

    async def storage_balance_of(
        self, ft: Union[FtModel, str], account_id: Optional[str] = None
    ) -> int:
        """
        Get storage balance of account. The balance must be greater than 0.01 NEAR for some smart contracts
        in order for the recipient to accept the token

        :param contract_id: fungible token contract_id
        :param account_id: account id
        :return: int balance in yoctoNEAR, 1_000_000_000_000_000_000_000_000 for 1 NEAR
        """
        if not account_id:
            account_id = self._account.account_id
        if isinstance(ft, FtModel):
            contract_id = ft.contract_id
        else:
            contract_id = ft
        res = (
            await self._account.view_function(
                contract_id,
                "storage_balance_of",
                {"account_id": account_id},
            )
        ).result
        if res:
            return int(res["total"] or 0)
        return 0

    async def storage_deposit(
        self,
        ft: Union[FtModel, str],
        account_id: Optional[str] = None,
        amount: int = NEAR // 50,
    ):
        """
        Deposit storage balance for account. The balance must be greater than 0.01 NEAR for some smart contracts

        :param ft: fungible token model FT.USDC
        :param account_id: receiver account id
        :param amount: in amount of yoctoNEAR
        :return:
        """
        if not account_id:
            account_id = self._account.account_id
        if isinstance(ft, FtModel):
            contract_id = ft.contract_id
        else:
            contract_id = ft
        return await self._account.function_call(
            contract_id,
            "storage_deposit",
            {"account_id": account_id},
            amount=amount,
        )
