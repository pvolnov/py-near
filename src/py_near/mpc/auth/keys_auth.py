import json
from hashlib import sha256
from typing import List

import base58
from nacl import signing

from py_near.account import Account
from py_near.mpc.auth.base import AuthContract
from py_near.mpc.models import WalletAccessModel


class KeysAuthContract(AuthContract):
    auth_keys: List[signing.SigningKey]
    auth_method: int
    contract_id: str = "keys.auth.hot.tg"

    def __init__(
        self,
        auth_keys: List[signing.SigningKey],
        auth_method=0,
        near_account: Account = None,
    ):
        self.auth_keys = auth_keys
        self.auth_method = auth_method
        super().__init__(near_account)

    def generate_user_payload(self, msg_hash: bytes):
        signatures = []
        for key in self.auth_keys:
            signatures.append(
                base58.b58encode(key.sign(msg_hash).signature).decode("utf-8")
            )
        return json.dumps(
            dict(
                signatures=signatures,
                auth_method=0,
            )
        )

    async def grant_access(
        self,
        wallet_id: str,
        access: WalletAccessModel,
        near_account,
        wallet_auth_method=0,
    ):
        access = access.model_dump()
        proof_hash = sha256(
            f"{json.dumps(access).replace(' ', '')}.{wallet_id}".encode("utf-8")
        ).digest()
        signatures = []
        for pk in self.auth_keys:
            signature = base58.b58encode(pk.sign(proof_hash).signature).decode("utf-8")
            signatures.append(signature)

        res = await near_account.function_call(
            self.contract_id,
            "add_wallet_auth_account_id",
            {
                "wallet_id": wallet_id,
                "access": access,
                "signatures": signatures,
                "wallet_auth_method": wallet_auth_method,
                "auth_method": self.auth_method,
            },
            included=True,
        )
        return res

    async def get_rules(self, wallet_id: str):
        if not self.near_account:
            raise ValueError("Near account is required")
        res = (
            await self.near_account.view_function(
                self.contract_id,
                "get_wallet",
                {
                    "wallet_id": wallet_id,
                },
            )
        ).result
        return res
