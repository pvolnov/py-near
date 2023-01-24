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
    async def transfer(
        self,
        receiver_id: str,
        amount: float,
        memo: str = "",
        nowait: bool = False,
    ):
        """
        Transfer hNEAR to account

        :param receiver_id: receiver account id
        :param amount: amount in yoctoNEAR
        :param memo: comment
        :param nowait if True, method will return before transaction is confirmed
        :return: transaction hash ot TransactionResult
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
        Transfer hNEAR to account and call ft_on_transfer() method in receiver contract

        :param receiver_id: receiver account id
        :param amount: amount in yoctoNEAR
        :param memo: comment
        :param nowait if True, method will return before transaction is confirmed
        :return: transaction hash ot TransactionResult
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
        Get staking balance of account.

        :param account_id: account id
        :param nowait if True, method will return before transaction is confirmed
        :return: int balance in yoctoNEAR
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
        Get user staking parameters

        :param account_id: account id
        :return: StakingData
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
        Deposit staking for account

        :param amount: in amount of yoctoNEAR
        :param nowait: if True, method will return before transaction is confirmed
        :return: transaction hash or TransactionResult
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
        Withdraw from staking

        :param amount: in amount of yoctoNEAR
        :param nowait: if True, method will return before transaction is confirmed
        :return: transaction hash or TransactionResult
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
        Receive dividends

        :param nowait: if True, method will return before transaction is confirmed
        :return: transaction hash ot TransactionResult
        """
        return await self._account.function_call(
            CONTRACT_ID[self._account.chain_id],
            "receive_dividends",
            {},
            amount=1,
            nowait=nowait,
        )
