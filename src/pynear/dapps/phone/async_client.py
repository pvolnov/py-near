import json
import re
from typing import List

import aiohttp
from pynear.dapps.core import DappClient, NEAR
from pynear.dapps.fts import FtModel
from pynear.dapps.phone.exceptions import RequestLimitError
from pynear.dapps.phone.models import NearTrustTransaction, FtTrustTransaction
from pynear.exceptions.exceptions import FunctionCallError

_PHONE_CONTRACT_ID = "phone.herewallet.near"


class Phone(DappClient):
    """
    Client to phone.herewallet.near contract
    With this contract you can send NEAR and fungible tokens to
    phone number. Reciver will get notification with link to claim tokens.
    """

    def __init__(self, account, api_key="default"):
        """

        :param account:
        :param api_key: there is limit for hash generator requests to provide spam,
         to make unlimited requests use api key. You can get it for free by contacting team@herewallet.app
        :param network: "mainnet" or "testnet"
        """
        if account.chain_id != "mainnet":
            raise ValueError("Only mainnet is supported")
        super().__init__(account)
        self._api_key = api_key

    async def _get_phone_hex(self, phone) -> str:
        """
        To calculate hash we need call herewallet api. This is necessary to prevent creation hash <> phone table.
        :param phone:
        :return: phone hash
        """
        if phone[0] != "+":
            raise ValueError("Phone number must start with +")
        phone = re.sub(r"\D", "", phone)
        async with aiohttp.ClientSession() as session:
            r = await session.get(
                f"https://api.herewallet.app/api/v1/phone/calc_phone_hash?phone={phone}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self._api_key,
                },
            )
            if r.status == 403:
                raise RequestLimitError(
                    "Too many hash generator requests, to make unlimited requests user api key."
                    "Contact team@herewallet.app to get it for free"
                )
            if r.status != 200:
                raise Exception(f"Error while getting phone hash: {r.status}\n{await r.text()}")
            content = json.loads(await r.text())
            return content["hash"]

    async def get_ft_transfers(self, phone: str) -> List[FtTrustTransaction]:
        """
        Get list of fungible token transfers to phone number
        :param phone: phone number
        :return: list of FtTrustTransaction
        """
        res = (
            await self._account.view_function(
                _PHONE_CONTRACT_ID,
                "get_ft_transfers",
                {"phone": await self._get_phone_hex(phone)},
            )
        ).result
        if res is None:
            return []
        return [FtTrustTransaction(**i) for i in res]

    async def get_near_transfers(self, phone: str) -> List[NearTrustTransaction]:
        """
        Get list of NEAR transfers to phone number
        :param phone: phone number
        :return: list of NEAR transfers
        """
        res = (
            await self._account.view_function(
                _PHONE_CONTRACT_ID,
                "get_transfers",
                {"phone": await self._get_phone_hex(phone)},
            )
        ).result
        if res is None:
            return []
        return [NearTrustTransaction(**i) for i in res]

    async def send_near_to_phone(
        self, phone: str, amount: float, comment: str = "", nowait: bool = False
    ):
        """
        Send NEAR to phone number. Receiver will get sms with link to claim tokens.
        :param phone: +X format phone number
        :param amount: number of NEAR which will be sent
        :param comment: any comment
        :param nowait if True, method will return before transaction is confirmed
        :return: transaction hash ot TransactionResult
        """
        if amount < 0.1:
            raise ValueError("Amount must be >= 0.1 NEAR")
        return await self._account.function_call(
            _PHONE_CONTRACT_ID,
            "send_near_to_phone",
            {"phone": await self._get_phone_hex(phone), "comment": comment},
            amount=int(amount * NEAR),
            nowait=nowait,
        )

    async def send_ft_to_phone(
        self,
        ft: FtModel,
        phone: str,
        amount: float,
        comment: str = "",
        nowait: bool = False,
    ):
        """
        Send fungible token to phone number. Reciver will get sms with link to claim tokens.
        :param ft: Fungible token model
        :param phone: +X format phone number
        :param amount: number of FT which will be sent
        :param comment:
        :param nowait: if True, method will return before transaction is confirmed
        :return:
        """
        return await self._account.function_call(
            ft.contract_id,
            "ft_transfer_call",
            {
                "msg": await self._get_phone_hex(phone),
                "comment": comment,
                "receiver_id": _PHONE_CONTRACT_ID,
                "amount": str(int(amount * 10**ft.decimal)),
            },
            amount=1,
            nowait=nowait,
        )

    async def cancel_near_transaction(self, phone: str, index: int):
        """
        Cancel NEAR transfer to phone number. Use index from get_near_transfers() method
        :param phone: phone number
        :param index: index in transaction list
        :return:
        """
        try:
            return await self._account.function_call(
                _PHONE_CONTRACT_ID,
                "cancel_near_transaction",
                {"phone": await self._get_phone_hex(phone), "index": index},
                amount=1,
            )
        except FunctionCallError as e:
            if "`None` value" in str(e.error):
                raise ValueError(f"Transaction with index {index} not found")
            raise e

    async def cancel_ft_transaction(self, phone: str, index: int):
        """
        Cancel fungible token transfer to phone number. Use index from get_ft_transfers() method
        :param phone: phone number
        :param index: index in transaction list
        :return:
        """
        try:
            return await self._account.function_call(
                _PHONE_CONTRACT_ID,
                "cancel_ft_transaction",
                {"phone": await self._get_phone_hex(phone), "index": index},
                amount=1,
            )
        except FunctionCallError as e:
            if "`None` value" in str(e):
                raise ValueError(f"Transaction with index {index} not found")
            raise e
