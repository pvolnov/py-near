import json
import re
from typing import List

import aiohttp

from async_near.dapps.core import DappClient, NEAR
from async_near.dapps.fts import FtModel
from async_near.dapps.phone.exceptions import RequestLimitError
from async_near.dapps.phone.models import NearTrustTransaction, FtTrustTransaction

_PHONE_CONTRACT_ID = "phone.herewallet.near"


class Phone(DappClient):
    def __init__(self, account, api_key="default"):
        super().__init__(account)
        self._api_key = api_key

    async def _get_phone_hex(self, phone):
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
                raise Exception(
                    f"Error while getting phone hash: {r.status}\n{await r.text()}"
                )
            content = json.loads(await r.text())
            return content["hash"]

    async def get_ft_transfers(self, phone: str) -> List[FtTrustTransaction]:
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

    async def send_near_to_phone(self, phone: str, amount: float, comment: str = ""):
        """

        :param phone: +X format phone number
        :param amount: number of NEAR which will be sent
        :param comment:
        :return:
        """
        return await self._account.function_call(
            _PHONE_CONTRACT_ID,
            "send_near_to_phone",
            {"phone": await self._get_phone_hex(phone), "comment": comment},
            amount=int(amount * NEAR),
        )

    async def send_ft_to_phone(
        self, ft: FtModel, phone: str, amount: float, comment: str = ""
    ):
        """

        :param ft: Fungible token model
        :param phone: +X format phone number
        :param amount: number of FT which will be sent
        :param comment:
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
        )

    async def cancel_near_transaction(self, phone: str, index: int):
        return await self._account.function_call(
            _PHONE_CONTRACT_ID,
            "cancel_near_transaction",
            {"phone": await self._get_phone_hex(phone), "index": index},
            amount=1,
        )

    async def cancel_ft_transaction(self, phone: str, index: int):
        return await self._account.function_call(
            _PHONE_CONTRACT_ID,
            "cancel_ft_transaction",
            {"phone": await self._get_phone_hex(phone), "index": index},
            amount=1,
        )
