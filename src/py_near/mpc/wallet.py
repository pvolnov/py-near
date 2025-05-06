import json
from hashlib import sha256
from typing import List, Optional

import base58
import httpx
from eth_keys.datatypes import Signature
from eth_keys.exceptions import BadSignature
from eth_utils import keccak
from loguru import logger
from nacl import encoding, signing

from py_near.account import Account
from py_near.mpc.auth.auth_2fa import AuthContract2FA
from py_near.mpc.auth.base import AuthContract
from py_near.mpc.auth.default_auth import DefaultAuthContract
from py_near.mpc.auth.keys_auth import KeysAuthContract
from py_near.mpc.models import WalletAccessModel, WalletModel, CurveType

_WALLET_REGISTER = "mpc.hot.tg"

AUTH_CLASS = {
    "default.auth.hot.tg": DefaultAuthContract,
    "keys.auth.hot.tg": KeysAuthContract,
    "2fa.auth.hot.tg": AuthContract2FA,
}


class MPCWallet:
    derive: bytes
    near_account: Account
    hot_rpc: str

    def __init__(
        self,
        near_account: Account,
        default_root_pk: Optional[bytes] = None,
        hot_rpc: str = "https://rpc1.hotdao.ai",
        derive: Optional[bytes] = None,
    ):
        """
        :param near_account: Near account
        :param derive: Derived key for wallet
        :param hot_rpc: Hot RPC url
        :param default_root_pk: Default auth key for HOT Protocol, if provided, derive = sha256(default_root_pk.public_key).digest()
        """
        self.near_account = near_account
        if len(default_root_pk) != 32:
            raise ValueError("Default root pk should be 32 bytes")
        if default_root_pk:
            self.default_root_pk = default_root_pk
            private_key_obj = self.derive_private_key(0)
            derive = sha256(private_key_obj.verify_key.encode()).digest()
        elif derive is None:
            logger.warning(
                "Its recomended to use default_root_pk to generate derives, v0 wallets support will be deprecated"
            )
            raise ValueError("Derive is required")
        self.derive = derive
        self.hot_rpc = hot_rpc
        self._client = httpx.AsyncClient()

    def derive_private_key(self, gen=0):
        private_key = self.default_root_pk
        for _ in range(gen):
            private_key = sha256(private_key).digest()
        return signing.SigningKey(
            private_key,
            encoder=encoding.RawEncoder,
        )

    @property
    def wallet_id(self):
        return base58.b58encode(sha256(self.derive).digest()).decode("utf-8")

    async def get_wallet(self):
        wallet = await self.near_account.view_function(
            _WALLET_REGISTER, "get_wallet", args={"wallet_id": self.wallet_id}
        )
        if wallet.result:
            return WalletModel.build(wallet.result)

    async def create_wallet_with_keys_auth(self, public_key: bytes, key_gen=1):
        """
        Create wallet with keys.auth.hot.tg auth method.
        :param public_key: Public key for auth future signs on keys.auth.hot.tg
        """
        wallet = await self.get_wallet()
        if wallet and wallet.access_list[0].account_id != "default.auth.hot.tg":
            raise ValueError(
                "MPCWallet already exists with different auth method, please use another wallet_id"
            )
        auth_to_add_msg = json.dumps(
            dict(public_keys=[base58.b58encode(public_key).decode()], rules=[])
        ).replace(" ", "")
        return await self.create_wallet(
            "keys.auth.hot.tg", None, auth_to_add_msg, key_gen
        )

    async def create_wallet(
        self, auth_account_id: str, metadata: str = "", auth_to_add_msg="", key_gen=1
    ):
        """
        Create wallet with keys.auth.hot.tg auth method.
        :param public_key: Public key for auth future signs on keys.auth.hot.tg
        """
        wallet = await self.get_wallet()
        if wallet and wallet.access_list[0].account_id != "default.auth.hot.tg":
            raise ValueError(
                "MPCWallet already exists with different auth method, please use another wallet_id"
            )
        root_pk = self.derive_private_key(0)
        proof_hash = sha256(
            f"CREATE_WALLET:{self.wallet_id}:{auth_account_id}:{metadata}:{auth_to_add_msg}".encode(
                "utf-8"
            )
        ).digest()
        signature = base58.b58encode(root_pk.sign(proof_hash).signature).decode("utf-8")

        s = await self._client.post(
            f"{self.hot_rpc}/create_wallet",
            json=dict(
                wallet_id=self.wallet_id,
                key_gen=key_gen,
                signature=signature,
                wallet_derive_public_key=base58.b58encode(
                    root_pk.verify_key.encode()
                ).decode(),
                auth={
                    "auth_account_id": auth_account_id,
                    "msg": auth_to_add_msg,
                    "metadata": metadata or None,
                },
            ),
            timeout=30,
        )
        return s.json()

    async def get_ecdsa_public_key(self) -> bytes:
        resp = (
            await self._client.post(
                f"{self.hot_rpc}/public_key",
                json=dict(wallet_derive=base58.b58encode(self.derive).decode()),
                timeout=10,
                follow_redirects=True,
            )
        ).json()
        return bytes.fromhex(resp["ecdsa"])

    @property
    def public_key(self):
        # TODO Calculate with Rust Code
        raise NotImplementedError("Public key calculation is not implemented yet")

    async def sign_message(
        self,
        msg_hash: bytes,
        message_body: Optional[bytes] = None,
        curve_type: CurveType = CurveType.SECP256K1,
        auth_methods: List[AuthContract] = None,
    ):
        if not self.default_root_pk:
            raise ValueError("Default auth key is required")
        wallet = await self.get_wallet()
        user_payloads = []
        if len(auth_methods) != len(wallet.access_list):
            raise ValueError("Auth methods count should be equal to wallet access list")

        for auth_contract, auth_method in zip(auth_methods, wallet.access_list):
            user_payloads.append(auth_contract.generate_user_payload(msg_hash))

        proof = {
            "auth_id": 0,
            "curve_type": curve_type,
            "user_payloads": user_payloads,
            "message_body": message_body.hex() if message_body else "",
        }

        resp = await self._client.post(
            f"{self.hot_rpc}/sign_raw",
            json=dict(
                uid=self.derive.hex(),
                message=msg_hash.hex(),
                proof=proof,
                key_type=curve_type,
            ),
            timeout=10,
            follow_redirects=True,
        )
        resp = resp.json()
        if "Ecdsa" not in resp:
            raise ValueError(f"Invalid response from server: {resp}")
        resp = resp["Ecdsa"]
        r = int(resp["big_r"][2:], 16)
        s = int(resp["signature"], 16)

        pk = await self.get_ecdsa_public_key()
        for v in (0, 1):
            sig = Signature(vrs=(v, r, s))
            recovered = sig.recover_public_key_from_msg_hash(msg_hash)
            if recovered.to_compressed_bytes() == pk:
                return (
                    r.to_bytes(32, "big") + s.to_bytes(32, "big") + bytes([v])
                ).hex()

        raise BadSignature("Cannot recover public key from signature")

    async def add_new_access_rule(
        self, access: WalletAccessModel, auth_contracts: List[AuthContract]
    ):
        wallet = await self.get_wallet()
        access_json = access.model_dump_json()
        message_body = f"ADD_AUTH_METHOD:{access_json}:{self.wallet_id}".encode("utf-8")
        msg_hash = sha256(message_body).digest()
        user_payloads = []
        for auth_contract, auth_method in zip(auth_contracts, wallet.access_list):
            auth_class = AUTH_CLASS[auth_method.account_id]
            if not isinstance(auth_contract, auth_class):
                raise ValueError(
                    f"Auth method {auth_method.account_id} is not supported for this auth class"
                )
            user_payloads.append(auth_contract.generate_user_payload(msg_hash))
        return await self.near_account.function_call(
            _WALLET_REGISTER,
            "add_access_rule",
            {
                "wallet_id": self.wallet_id,
                "rule": access.model_dump(),
                "user_payloads": user_payloads,
            },
            included=True,
        )

    async def remove_access_rule(
        self, access_id: int, auth_contracts: List[AuthContract]
    ):
        wallet = await self.get_wallet()
        message_body = f"REMOVE_AUTH_METHOD:{access_id}:{self.wallet_id}".encode(
            "utf-8"
        )
        msg_hash = sha256(message_body).digest()
        user_payloads = []
        if len(auth_contracts) != len(wallet.access_list):
            raise ValueError("Auth methods count should be equal to wallet access list")
        for auth_contract, auth_method in zip(auth_contracts, wallet.access_list):
            auth_class = AUTH_CLASS[auth_method.account_id]
            if not isinstance(auth_contract, auth_class):
                raise ValueError(
                    f"Auth method {auth_method.account_id} is not supported for this auth class"
                )
            user_payloads.append(auth_contract.generate_user_payload(msg_hash))
        return await self.near_account.function_call(
            _WALLET_REGISTER,
            "remove_access_rule",
            {
                "wallet_id": self.wallet_id,
                "rule_id": access_id,
                "user_payloads": user_payloads,
            },
            included=True,
        )