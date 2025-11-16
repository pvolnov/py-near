import json
from hashlib import sha256
from typing import List, Optional

import aiohttp
import base58
from eth_keys.datatypes import Signature
from eth_keys.exceptions import BadSignature
from loguru import logger
from nacl import encoding, signing

from py_near.account import Account
from py_near.mpc.auth.base import AuthContract
from py_near.mpc.auth.default_auth import DefaultAuthContract
from py_near.mpc.auth.keys_auth import KeysAuthContract
from py_near.mpc.models import WalletAccessModel, WalletModel, CurveType

_WALLET_REGISTER = "mpc.hot.tg"

AUTH_CLASS = {
    "default.auth.hot.tg": DefaultAuthContract,
    "keys.auth.hot.tg": KeysAuthContract,
}


class MPCWallet:
    """
    Multi-Party Computation (MPC) wallet client for HOT Protocol.

    Provides methods for managing MPC wallets, signing messages, and interacting
    with HOT Protocol's wallet registration system.
    """

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
        Initialize MPC wallet instance.

        Args:
            near_account: NEAR account instance for blockchain interactions
            default_root_pk: Default authentication key for HOT Protocol (32 bytes).
                If provided, derive is automatically calculated as
                sha256(default_root_pk.public_key).digest()
            hot_rpc: HOT Protocol RPC endpoint URL
            derive: Derived key for wallet (required if default_root_pk is not provided)

        Raises:
            ValueError: If default_root_pk is not 32 bytes, or if neither
                default_root_pk nor derive is provided
        """
        self.near_account = near_account
        if default_root_pk:
            if len(default_root_pk) != 32:
                raise ValueError("Default root pk should be 32 bytes")
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
        self._connector = aiohttp.TCPConnector()
        self._client = aiohttp.ClientSession(connector=self._connector)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.shutdown()

    async def shutdown(self):
        """Shutdown the wallet and close HTTP client connections."""
        if not self._client.closed:
            await self._client.close()
        if not self._connector.closed:
            await self._connector.close()

    def derive_private_key(self, gen=0):
        """
        Derive a private key for a specific generation.

        Args:
            gen: Generation number (0 for root key, higher for derived keys)

        Returns:
            SigningKey instance for the derived private key
        """
        private_key = self.default_root_pk
        for _ in range(gen):
            private_key = sha256(private_key).digest()
        return signing.SigningKey(
            private_key,
            encoder=encoding.RawEncoder,
        )

    @property
    def wallet_id(self):
        """
        Get wallet ID derived from the derive key.

        Returns:
            Base58-encoded wallet ID string
        """
        return base58.b58encode(sha256(self.derive).digest()).decode("utf-8")

    async def get_wallet(self):
        """
        Get wallet information from the blockchain.

        Returns:
            WalletModel instance if wallet exists, None otherwise
        """
        wallet = await self.near_account.view_function(
            _WALLET_REGISTER, "get_wallet", args={"wallet_id": self.wallet_id}
        )
        if wallet.result:
            return WalletModel.build(wallet.result)

    async def create_wallet_with_keys_auth(self, public_key: bytes, key_gen=1):
        """
        Create wallet with keys.auth.hot.tg authentication method.

        Args:
            public_key: Public key for future authentication signatures on keys.auth.hot.tg
            key_gen: Key generation number (default: 1)

        Returns:
            Dictionary containing wallet creation response

        Raises:
            ValueError: If wallet already exists with a different auth method
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
            "keys.auth.hot.tg", "", auth_to_add_msg, key_gen
        )

    async def create_wallet(
        self,
        auth_account_id: str,
        metadata: str = "",
        auth_to_add_msg="",
        key_gen=1,
        timeout=30,
    ):
        """
        Create wallet with specified authentication method.

        Args:
            auth_account_id: Authentication account ID (e.g., "keys.auth.hot.tg")
            metadata: Optional metadata string
            auth_to_add_msg: Optional message for authentication setup
            key_gen: Key generation number (default: 1)
            timeout: Request timeout in seconds (default: 30)

        Returns:
            Dictionary containing wallet creation response

        Raises:
            ValueError: If wallet already exists with a different auth method
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

        async with self._client.post(
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
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as s:
            return await s.json()

    async def get_ecdsa_public_key(self, timeout=10) -> bytes:
        """
        Get ECDSA public key from HOT RPC.

        Args:
            timeout: Request timeout in seconds (default: 10)

        Returns:
            ECDSA public key as bytes
        """
        async with self._client.post(
            f"{self.hot_rpc}/public_key",
            json=dict(wallet_derive=base58.b58encode(self.derive).decode()),
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as resp:
            data = await resp.json()
            return bytes.fromhex(data["ecdsa"])

    @property
    def public_key(self):
        """
        Get public key (not yet implemented).

        Returns:
            Public key (currently raises NotImplementedError)

        Raises:
            NotImplementedError: Public key calculation is not implemented yet
        """
        # TODO Calculate with Rust Code
        raise NotImplementedError("Public key calculation is not implemented yet")

    async def sign_message(
        self,
        msg_hash: bytes,
        message_body: Optional[bytes] = None,
        curve_type: CurveType = CurveType.SECP256K1,
        auth_methods: List[AuthContract] = None,
        timeout=10,
    ):
        """
        Sign a message using MPC wallet.

        Args:
            msg_hash: Hash of the message to sign (bytes)
            message_body: Optional raw message body (bytes)
            curve_type: Curve type for signing (default: SECP256K1)
            auth_methods: List of authentication contracts for signing
            timeout: Request timeout in seconds (default: 10)

        Returns:
            Hexadecimal signature string

        Raises:
            ValueError: If default_root_pk is not set, or if auth_methods count
                doesn't match wallet access list, or if server returns invalid response
            BadSignature: If public key cannot be recovered from signature
        """
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

        async with self._client.post(
            f"{self.hot_rpc}/sign_raw",
            json=dict(
                uid=self.derive.hex(),
                message=msg_hash.hex(),
                proof=proof,
                key_type=curve_type,
            ),
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as resp:
            resp_data = await resp.json()
        if "Ecdsa" not in resp_data:
            raise ValueError(f"Invalid response from server: {resp_data}")
        resp = resp_data["Ecdsa"]
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
        """
        Add a new access rule to the wallet.

        Args:
            access: WalletAccessModel containing access rule configuration
            auth_contracts: List of authentication contracts for signing the transaction

        Returns:
            Transaction hash (str) or TransactionResult

        Raises:
            ValueError: If auth method types don't match wallet access list
        """
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
        """
        Remove an access rule from the wallet.

        Args:
            access_id: ID of the access rule to remove
            auth_contracts: List of authentication contracts for signing the transaction

        Returns:
            Transaction hash (str) or TransactionResult

        Raises:
            ValueError: If auth methods count doesn't match wallet access list,
                or if auth method types don't match
        """
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
