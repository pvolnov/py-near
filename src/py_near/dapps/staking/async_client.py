from typing import Optional

from py_near.dapps.core import DappClient
from py_near.dapps.staking.exceptions import NotEnoughBalance
from py_near.dapps.staking.models import StakingData
from py_near.exceptions.exceptions import FunctionCallError

CONTRACT_ID = {
    "mainnet": "storage.herewallet.near",
    "testnet": "storage.herewallet.testnet",
}


class Staking(DappClient):
    """
    Client for interacting with staking operations on NEAR.

    Provides methods for staking NEAR, unstaking, transferring staked tokens,
    and managing staking-related operations.
    """

    async def transfer(
        self,
        receiver_id: str,
        amount: float,
        memo: str = "",
        nowait: bool = False,
    ):
        """
        Transfer staked tokens (hNEAR) to another account.

        Args:
            receiver_id: Receiver account ID
            amount: Amount to transfer as float
            memo: Optional memo/comment for the transfer
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult

        Raises:
            NotEnoughBalance: If sender has insufficient balance
        """

        try:
            return await self._account.function_call(
                CONTRACT_ID[self._account.chain_id],
                "ft_transfer",
                {
                    "receiver_id": receiver_id,
                    "amount": str(amount),
                    "msg": memo,
                },
                amount=1,
                nowait=nowait,
            )
        except FunctionCallError as e:
            if "The account doesn't have enough balance" in e.error["ExecutionError"]:
                raise NotEnoughBalance(e)
            raise e

    async def transfer_call(
        self,
        receiver_id: str,
        amount: int,
        memo: str = "",
        nowait: bool = False,
    ):
        """
        Transfer staked tokens and call ft_on_transfer() on receiver contract.

        Args:
            receiver_id: Receiver account/contract ID
            amount: Amount to transfer as integer
            memo: Optional memo/comment for the transfer
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        return await self._account.function_call(
            CONTRACT_ID[self._account.chain_id],
            "ft_transfer_call",
            {
                "receiver_id": receiver_id,
                "amount": str(amount),
                "msg": memo,
            },
            amount=1,
            nowait=nowait,
        )

    async def get_staking_amount(self, account_id: str = None) -> int:
        """
        Get staking balance for an account.

        Args:
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            Staking balance in yoctoNEAR (0 if account has no staked tokens)
        """
        if account_id is None:
            account_id = self._account.account_id
        res = (
            await self._account.view_function(
                CONTRACT_ID[self._account.chain_id],
                "ft_balance_of",
                {"account_id": account_id},
            )
        ).result
        if res:
            return int(res)
        return 0

    async def get_user(self, account_id: str = None) -> Optional[StakingData]:
        """
        Get user staking parameters and information.

        Args:
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            StakingData containing staking parameters, or None if not found
        """
        if account_id is None:
            account_id = self._account.account_id
        res = (
            await self._account.view_function(
                CONTRACT_ID[self._account.chain_id],
                "get_user",
                {"account_id": account_id},
            )
        ).result
        if res:
            return StakingData(**res)

    async def stake(self, amount: int, nowait: bool = False):
        """
        Deposit NEAR for staking.

        Args:
            amount: Amount to stake in yoctoNEAR
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        return await self._account.function_call(
            CONTRACT_ID[self._account.chain_id],
            "storage_deposit",
            {},
            amount=amount,
            nowait=nowait,
        )

    async def unstake(self, amount: int, nowait: bool = False):
        """
        Withdraw NEAR from staking.

        Args:
            amount: Amount to unstake in yoctoNEAR
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult

        Raises:
            NotEnoughBalance: If account has insufficient staked balance
        """
        try:
            return await self._account.function_call(
                CONTRACT_ID[self._account.chain_id],
                "storage_withdraw",
                {"amount": str(int(amount))},
                amount=1,
                nowait=nowait,
            )
        except FunctionCallError as e:
            if "The account doesn't have enough balance" in e:
                raise NotEnoughBalance
            raise e

    async def receive_dividends(self, nowait=False):
        """
        Receive staking dividends/rewards.

        Args:
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        return await self._account.function_call(
            CONTRACT_ID[self._account.chain_id],
            "receive_dividends",
            {},
            amount=1,
            nowait=nowait,
        )
