from typing import Union

from py_near.dapps.ft.exceptions import NotRegisteredError, NotEnoughBalance
from py_near.exceptions.exceptions import FunctionCallError

from py_near.dapps.core import DappClient, NEAR
from py_near.dapps.ft.models import FtTokenMetadata
from py_near.dapps.fts import FtModel
from typing import Optional


class FT(DappClient):
    """
    Client for interacting with fungible tokens (FT) on NEAR.

    Provides methods for querying balances, transferring tokens, and managing
    storage deposits for FT contracts following the NEP-141 standard.
    """

    async def get_ft_balance(
        self, ft: FtModel, account_id: Optional[str] = None
    ) -> float:
        """
        Get fungible token balance for an account.

        Args:
            ft: Fungible token model (e.g., FT.USDC)
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            Token balance as float (amount divided by 10^ft.decimal)
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
        Get fungible token raw balance (without decimal conversion).

        Args:
            contract_id: Fungible token contract address
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            Raw token balance as integer (in smallest token unit)
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
        Get fungible token metadata.

        Args:
            ft: Fungible token model (e.g., FT.USDC) or contract ID string

        Returns:
            FtTokenMetadata containing token name, symbol, decimals, etc.
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
        Transfer fungible tokens to another account.

        Args:
            ft: Fungible token model (e.g., FT.USDC)
            receiver_id: Receiver account ID
            amount: Amount to transfer as float (e.g., 1.0 for 1 USDC)
            memo: Optional memo/comment for the transfer
            force_register: If True, automatically register receiver with storage_deposit
                if they are not registered
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult

        Raises:
            NotRegisteredError: If receiver is not registered and force_register is False
            NotEnoughBalance: If sender has insufficient balance
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
        Transfer fungible tokens and call ft_on_transfer() on receiver contract.

        This method transfers tokens and then calls the ft_on_transfer callback
        method on the receiver's contract, enabling atomic token transfers with
        contract logic execution.

        Args:
            ft: Fungible token model (e.g., FT.USDC)
            receiver_id: Receiver account/contract ID
            amount: Amount to transfer as float (e.g., 1.0 for 1 USDC)
            memo: Optional memo/comment for the transfer
            force_register: If True, automatically register receiver with storage_deposit
                if they are not registered
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
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
        Get storage balance for an account on an FT contract.

        Some FT contracts require accounts to have a storage deposit (typically
        >= 0.01 NEAR) before they can receive tokens.

        Args:
            ft: Fungible token model (e.g., FT.USDC) or contract ID string
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            Storage balance in yoctoNEAR (0 if account is not registered)
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
        Deposit storage balance for an account on an FT contract.

        Registers an account with the FT contract and deposits NEAR for storage.
        This is required before an account can receive tokens from some contracts.

        Args:
            ft: Fungible token model (e.g., FT.USDC) or contract ID string
            account_id: Account ID to register. If None, uses the current account.
            amount: Amount to deposit in yoctoNEAR (default: 0.02 NEAR)

        Returns:
            Transaction hash (str) or TransactionResult
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
