"""Intent manager for omni_balance operations."""

import asyncio
import base64
import collections
import datetime
import json
import random
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import base58
from loguru import logger
from nacl import signing as ed25519, encoding

from py_near.account import Account, ViewFunctionError
from py_near.constants import RPC_MAINNET, TGAS
from py_near.dapps.nft.models import NftMetadata
from py_near.exceptions.provider import InternalError
from py_near.models import TransactionResult
from py_near.omni_balance.constants import (
    SOLVER_BUS_URL,
    INTENTS_CONTRACT,
    INTENTS_HEADERS,
    MAX_GAS,
)
from py_near.omni_balance.exceptions import SimulationError
from py_near.omni_balance.models import (
    Commitment,
    IntentAuthCallback,
    IntentMtWithdraw,
    IntentNftWithdraw,
    NativeWithdraw,
    SimulationResult,
    IntentTokenDiff,
    IntentTransfer,
    IntentType,
    Quote,
)


class IntentBuilder:
    """Builder for creating and submitting intents."""

    def __init__(self, manager: "OmniBalance") -> None:
        """Initialize IntentBuilder with OmniBalance manager."""
        self.manager = manager
        self._intents: List[IntentType] = []
        self.nonce: Optional[str] = None
        self.deadline_seconds: Optional[int] = None
        self.seed: Optional[str] = None
        self._token_diff = collections.defaultdict(int)
        self.referral = None

    @property
    def intents(self):
        intents = self._intents
        if self._token_diff:
            diff = {}
            for token, amount in self._token_diff.items():
                if amount != 0:
                    diff[token] = str(amount)
            if diff:
                intents.append(IntentTokenDiff(diff=diff, referral=self.referral))
        return intents

    def transfer(
        self,
        tokens: Dict[str, str],
        receiver_id: str,
        memo: Optional[str] = None,
        msg: Optional[str] = None,
        min_gas: Optional[str] = None,
    ) -> "IntentBuilder":
        """Add transfer intent."""
        self._intents.append(
            IntentTransfer(
                tokens=tokens,
                receiver_id=receiver_id,
                memo=memo,
                msg=msg,
                min_gas=min_gas,
            )
        )
        return self

    def token_diff(
        self,
        diff: Dict[str, str],
        referral: Optional[str] = None,
    ) -> "IntentBuilder":
        """Add token diff intent."""
        self._intents.append(IntentTokenDiff(diff=diff, referral=referral))
        return self

    def take(
        self,
        token: str,
        amount: Union[str, int],
    ) -> "IntentBuilder":
        """Add token diff intent."""
        self._token_diff[token] += int(amount)
        return self

    def give(
        self,
        token: str,
        amount: Union[str, int],
    ) -> "IntentBuilder":
        """Add token diff intent."""
        self._token_diff[token] -= int(amount)
        return self

    def mt_withdraw(
        self,
        token_ids: List[str],
        amounts: List[str],
        receiver_id: str,
        msg: str,
        token: str = "v2_1.omni.hot.tg",
    ) -> "IntentBuilder":
        """Add multi-token withdraw intent."""
        self._intents.append(
            IntentMtWithdraw(
                token=token,
                receiver_id=receiver_id,
                token_ids=token_ids,
                amounts=amounts,
                msg=msg,
            )
        )
        return self

    def nft_withdraw(
        self,
        contract_id: str,
        token_id: str,
        receiver_id: str,
        msg: Optional[str] = None,
    ) -> "IntentBuilder":
        """Add NFT withdraw intent."""
        self._intents.append(
            IntentNftWithdraw(
                token=contract_id,
                token_id=token_id,
                receiver_id=receiver_id,
                msg=msg,
            )
        )
        return self

    def native_withdraw(
        self,
        receiver_id: str,
        amount: str,
        memo: Optional[str] = None,
    ) -> "IntentBuilder":
        """Add native NEAR withdraw intent."""
        self._intents.append(
            NativeWithdraw(
                receiver_id=receiver_id,
                amount=amount,
                memo=memo,
            )
        )
        return self

    def auth_call(
        self,
        contract_id: str,
        msg: str,
        attached_deposit: str = "0",
        min_gas: Optional[str] = None,
    ) -> "IntentBuilder":
        """Add auth callback intent."""
        self._intents.append(
            IntentAuthCallback(
                contract_id=contract_id,
                msg=msg,
                attached_deposit=attached_deposit,
                min_gas=min_gas,
            )
        )
        return self

    def mint_nft(
        self,
        contract_id: str,
        token_id: str,
        token_owner_id: str,
        token_metadata: NftMetadata,
        msg: Optional[str] = None,
    ) -> "IntentBuilder":
        """Wrapper to mint new NFT."""
        if not contract_id.endswith(".nfts.tg"):
            raise ValueError("Contract ID must end with .nfts.tg")
        self._intents.append(
            IntentAuthCallback(
                contract_id=contract_id,
                msg=json.dumps(
                    dict(
                        token_id=token_id,
                        token_owner_id=token_owner_id,
                        token_metadata=token_metadata.model_dump(
                            exclude_none=True, mode="json"
                        ),
                        msg=msg,
                    )
                ),
                min_gas=str(100 * TGAS),
            )
        )
        return self

    def burn_nft(
        self,
        token: str,
        token_id: str,
        burn_callback_receiver_id: Optional[str] = None,
        msg: Optional[str] = None,
        memo: Optional[str] = "burn",
    ) -> "IntentBuilder":
        """Wrapper to burn NFT."""
        if not token.endswith(".nfts.tg"):
            raise ValueError("Contract ID must end with .nfts.tg")
        burn_msg = None
        if burn_callback_receiver_id and msg:
            burn_msg = json.dumps(
                dict(
                    burn_callback_receiver_id=burn_callback_receiver_id,
                    msg=msg,
                )
            )
        self._intents.append(
            IntentNftWithdraw(
                token=token,
                token_id=token_id,
                receiver_id=token,
                memo=memo,
                msg=burn_msg,
            )
        )
        return self

    def with_nonce(self, nonce: Optional[str]) -> "IntentBuilder":
        """Set nonce for intents."""
        self.nonce = nonce
        return self

    def with_deadline(self, deadline_seconds: Optional[int]) -> "IntentBuilder":
        """Set deadline for intents."""
        self.deadline_seconds = deadline_seconds
        return self

    def with_referral(self, referral: str) -> "IntentBuilder":
        """Set deadline for intents."""
        self.referral = referral
        return self

    def with_seed(self, seed: Optional[str]) -> "IntentBuilder":
        """Set seed for nonce generation."""
        self.seed = seed
        return self

    def sign(self) -> Commitment:
        """Sign the intents and return commitment."""
        if not self.intents:
            raise ValueError("No intents to sign")
        nonce = self.manager._generate_nonce(self.seed or self.nonce)
        default_deadline = (
            60 if any(isinstance(i, IntentMtWithdraw) for i in self.intents) else 600
        )
        deadline_seconds = self.deadline_seconds or default_deadline
        quote = Quote(
            signer_id=self.manager.account_id,
            nonce=nonce,
            verifying_contract=self.manager.intents_contract,
            deadline=self.manager.get_deadline(deadline_seconds),
            intents=[
                i.model_dump(exclude_none=True, mode="json") for i in self.intents
            ],
        )
        return self.manager.sign_quote(quote)

    async def submit(self) -> str:
        """Sign and submit the intents."""
        commitment = self.sign()
        return await self.manager.publish_intents(commitment)

    def get_matched_token_diff(self) -> IntentTokenDiff:
        """Sign and submit the intents."""
        diff = {}
        for token, amount in self._token_diff.items():
            if amount > 0:
                diff[token] = str(-amount)
            else:
                diff[token] = str(amount)
        return IntentTokenDiff(diff=diff, referral=self.referral)

    def get_quote(self) -> Quote:
        """Get quote without signing."""
        if not self.intents:
            raise ValueError("No intents to create quote")
        nonce = self.manager._generate_nonce(self.seed or self.nonce)
        return Quote(
            signer_id=self.manager.account_id,
            nonce=nonce,
            verifying_contract=self.manager.intents_contract,
            deadline=self.manager.get_deadline(self.deadline_seconds),
            intents=[
                i.model_dump(exclude_none=True, mode="json") for i in self._intents
            ],
        )


class OmniBalance:
    """Intent manager for omni_balance operations."""

    def __init__(
        self,
        account_id: str,
        private_key: Union[List[str], str],
        rpc_urls: Union[str, List[str]] = None,
        intents_headers=None,
        solver_bus_url: str = SOLVER_BUS_URL,
        intents_contract: str = INTENTS_CONTRACT,
        **_: Any,
    ) -> None:
        """
        Initialize OmniBalance intent manager.

        Args:
            account_id: NEAR account ID
            private_key: List of private keys
            rpc_urls: RPC URL or list of URLs
        """
        if isinstance(private_key, str):
            private_key = [private_key]
        self.solver_bus_url = solver_bus_url
        self.intents_contract = intents_contract
        self.rpc_url: Union[str, List[str]] = rpc_urls or [RPC_MAINNET]
        self.account_id: str = account_id
        self.private_key: List[str] = private_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._account: Optional[Account] = None
        self._signing_key: Optional[ed25519.SigningKey] = None
        self._public_key: Optional[str] = None
        self.intents_headers: Optional[dict] = intents_headers or {}
        self.intents_headers.update(INTENTS_HEADERS)

    async def startup(self) -> "OmniBalance":
        """
        Initialize and start the OmniBalance manager.

        Creates HTTP session and initializes account connection.

        Returns:
            Self instance for method chaining
        """
        self._session = aiohttp.ClientSession()
        self._account = Account(
            self.account_id, self.private_key, rpc_addr=self.rpc_url
        )
        await self._account.startup()
        return self

    async def shutdown(self) -> None:
        """
        Shutdown and cleanup the OmniBalance manager.

        Closes HTTP session and releases resources.
        """
        if self._session:
            await self._session.close()
            self._session = None
        if self._account:
            await self._account.shutdown()
            self._account = None

    async def __aenter__(self) -> "OmniBalance":
        """Async context manager entry."""
        return await self.startup()

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit."""
        await self.shutdown()

    @property
    def signing_key(self) -> ed25519.SigningKey:
        """Get or create signing key."""
        if self._signing_key is None:
            self._signing_key = ed25519.SigningKey(
                base58.b58decode(self.private_key[0].replace("ed25519:", ""))[:32],
                encoder=encoding.RawEncoder,
            )
        return self._signing_key

    @property
    def public_key(self) -> str:
        """Get or create public key."""
        if self._public_key is None:
            self._public_key = "ed25519:" + base58.b58encode(
                self.signing_key.verify_key.encode()
            ).decode("utf-8")
        return self._public_key

    def _generate_nonce(self, seed: Optional[str] = None) -> str:
        """Generate nonce from seed or random."""
        data = (
            sha256(seed.encode()).digest()
            if seed
            else random.getrandbits(256).to_bytes(32, byteorder="big")
        )
        return base64.b64encode(data).decode("utf-8")

    def _get_public_key(self, public_key: Optional[str] = None) -> str:
        """Get public key, generating if not provided."""
        return public_key or self.public_key

    def _to_commitment_dict(self, commitment: Union[Commitment, dict]) -> dict:
        """Convert commitment to dict if needed."""
        if isinstance(commitment, Commitment):
            return commitment.to_dict()
        return commitment

    def _build_rpc_request(
        self, method: str, params: List[Any], headers: bool = False
    ) -> Tuple[dict, Optional[dict]]:
        """Build RPC request dict."""
        req = {"id": "dontcare", "jsonrpc": "2.0", "method": method, "params": params}
        return (req, self.intents_headers)

    @staticmethod
    def get_nonce(seed: Optional[str] = None, deadline_seconds: int = 600) -> str:
        """
        Generate nonce for intent.

        Args:
            seed: Optional seed for nonce generation
            deadline_seconds: Deadline in seconds

        Returns:
            Base64 encoded nonce
        """
        if seed:
            data = sha256(seed.encode()).digest()
        else:
            data = random.getrandbits(256).to_bytes(32, byteorder="big")
        nonce = base64.b64encode(data).decode("utf-8")
        return nonce

    @staticmethod
    def get_deadline(deadline_seconds: int = 600) -> str:
        """
        Get deadline string.

        Args:
            deadline_seconds: Deadline in seconds

        Returns:
            ISO formatted deadline string
        """
        return (
            datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(seconds=deadline_seconds)
        ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    async def register_token_storage(
        self, token_id: str, other_account: Optional[str] = None
    ) -> None:
        """
        Register token storage for account.

        Args:
            token_id: Token contract ID
            other_account: Optional account ID, defaults to self.account_id
        """
        account_id = other_account or self.account_id

        if not await self._account.view_function(
            token_id, "storage_balance_of", {"account_id": account_id}
        ):
            await self._account.function_call(
                token_id,
                "storage_deposit",
                {"account_id": account_id},
                MAX_GAS,
                1250000000000000000000,
            )

    def sign_quote(self, quote: Union[str, Quote]) -> Commitment:
        """
        Sign a quote.

        Args:
            quote: Quote object, JSON string, or dict

        Returns:
            Commitment with signature
        """
        if isinstance(quote, Quote):
            quote_data = quote.model_dump_json(exclude_none=True)
        elif isinstance(quote, str):
            quote_data = quote
        elif isinstance(quote, dict):
            quote_data = json.dumps(quote)
        else:
            raise ValueError(f"Invalid quote type: {type(quote)}")

        signed_message = self.signing_key.sign(quote_data.encode("utf-8"))
        signature = "ed25519:" + base58.b58encode(signed_message.signature).decode(
            "utf-8"
        )
        return Commitment(
            standard="raw_ed25519",
            payload=quote_data,
            signature=signature,
            public_key=self.public_key,
        )

    async def submit_signed_intent(
        self, signed_intents: Union[List[Commitment], Commitment]
    ) -> TransactionResult:
        """
        Submit signed intents to blockchain.

        Args:
            signed_intents: List of signed commitments

        Returns:
            Transaction result
        """
        if isinstance(signed_intents, Commitment):
            signed_intents = [signed_intents]
        return await self._account.function_call(
            self.intents_contract,
            "execute_intents",
            {
                "signed": [
                    i.model_dump(exclude_none=True, mode="json") for i in signed_intents
                ]
            },
            MAX_GAS,
            0,
            included=True,
        )

    async def deposit_near_token(self, token_id: str, amount: str) -> None:
        """
        Deposit NEAR token to intents contract.

        Args:
            token_id: Token contract ID
            amount: Amount to deposit
        """
        await self.register_token_storage(token_id, self.intents_contract)
        res = await self._account.function_call(
            token_id,
            "ft_transfer_call",
            {"receiver_id": self.intents_contract, "amount": amount, "msg": ""},
            MAX_GAS,
            1,
        )
        logger.info(f"Intent deposit {res.transaction.url}")

    async def deposit_nft(self, contract_id: str, token_id: str) -> None:
        """
        Deposit NFT to intents contract.

        Args:
            contract_id: NFT contract ID
            token_id: Token ID
        """
        res = await self._account.function_call(
            contract_id,
            "nft_transfer_call",
            {"token_id": token_id, "receiver_id": self.intents_contract, "msg": ""},
            MAX_GAS,
            1,
        )
        logger.info(f"Intent NFT deposit {res.transaction.url}")

    def intent(self) -> IntentBuilder:
        """Create a new IntentBuilder instance."""
        return IntentBuilder(self)

    def transfer(
        self,
        tokens: Dict[str, str],
        receiver_id: str,
        memo: Optional[str] = None,
        msg: Optional[str] = None,
        min_gas: Optional[str] = None,
    ) -> IntentBuilder:
        """
        Create transfer intent builder.

        Args:
            tokens: Dictionary of token_id -> amount
            receiver_id: Receiver account ID
            memo: Optional memo,
            msg: Optional message to call mt_on_transfer(..) on receiver address
            min_gas: Optional minimum gas

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).transfer(
            tokens=tokens, receiver_id=receiver_id, memo=memo, msg=msg, min_gas=min_gas
        )

    def token_diff(
        self,
        diff: Dict[str, str],
        referral: Optional[str] = None,
    ) -> IntentBuilder:
        """
        Create token diff intent builder.

        Args:
            diff: Dictionary of token differences
            referral: Optional referral

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).token_diff(diff=diff, referral=referral)

    def mt_withdraw(
        self,
        token_ids: List[str],
        amounts: List[str],
        receiver_id: str,
        msg: str,
        token: str = "v2_1.omni.hot.tg",
    ) -> IntentBuilder:
        """
        Create multi-token withdraw intent builder.

        Args:
            token_ids: List of token IDs
            amounts: List of amounts
            receiver_id: Receiver account ID
            msg: Message
            token: Token contract ID

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).mt_withdraw(
            token_ids=token_ids,
            amounts=amounts,
            receiver_id=receiver_id,
            msg=msg,
            token=token,
        )

    def auth_call(
        self,
        contract_id: str,
        msg: str,
        attached_deposit: str = "0",
        min_gas: Optional[str] = None,
    ) -> IntentBuilder:
        """
        Create auth callback intent builder.

        Args:
            contract_id: Contract ID
            msg: Message
            attached_deposit: Attached deposit amount
            min_gas: Minimum gas

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).auth_call(
            contract_id=contract_id,
            msg=msg,
            attached_deposit=attached_deposit,
            min_gas=min_gas,
        )

    def nft_withdraw(
        self,
        contract_id: str,
        token_id: str,
        receiver_id: str,
        msg: Optional[str] = None,
    ) -> IntentBuilder:
        """
        Create NFT withdraw intent builder.

        Args:
            contract_id: NFT contract ID
            token_id: Token ID
            receiver_id: Receiver account ID
            msg: Optional message

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).nft_withdraw(
            contract_id=contract_id,
            token_id=token_id,
            receiver_id=receiver_id,
            msg=msg,
        )

    def native_withdraw(
        self,
        receiver_id: str,
        amount: str,
        memo: Optional[str] = None,
    ) -> IntentBuilder:
        """
        Create native NEAR withdraw intent builder.

        Args:
            receiver_id: Receiver account ID
            amount: Amount to withdraw in NEAR
            memo: Optional memo

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).native_withdraw(
            receiver_id=receiver_id,
            amount=amount,
            memo=memo,
        )

    def take(
        self,
        token: str,
        amount: Union[str, int],
    ) -> IntentBuilder:
        """
        Create take intent builder.

        Args:
            token: Token contract ID
            amount: Amount to take

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).take(token=token, amount=amount)

    def give(
        self,
        token: str,
        amount: Union[str, int],
    ) -> IntentBuilder:
        """
        Create give intent builder.

        Args:
            token: Token contract ID
            amount: Amount to give

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).give(token=token, amount=amount)

    def mint_nft(
        self,
        contract_id: str,
        token_id: str,
        token_owner_id: str,
        token_metadata: NftMetadata,
        msg: Optional[str] = None,
    ) -> IntentBuilder:
        """
        Create mint NFT intent builder.

        Args:
            contract_id: NFT contract ID
            token_id: Token ID
            token_owner_id: Token owner account ID
            token_metadata: NFT metadata
            msg: Optional message

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).mint_nft(
            contract_id=contract_id,
            token_id=token_id,
            token_owner_id=token_owner_id,
            token_metadata=token_metadata,
            msg=msg,
        )

    def burn_nft(
        self,
        token: str,
        token_id: str,
        burn_callback_receiver_id: Optional[str] = None,
        msg: Optional[str] = None,
        memo: Optional[str] = "burn",
    ) -> IntentBuilder:
        """
        Create burn NFT intent builder.

        Args:
            token: NFT contract ID
            token_id: Token ID
            burn_callback_receiver_id: Optional burn callback receiver ID
            msg: Optional message
            memo: Optional memo

        Returns:
            IntentBuilder instance
        """
        return IntentBuilder(self).burn_nft(
            token=token,
            token_id=token_id,
            burn_callback_receiver_id=burn_callback_receiver_id,
            msg=msg,
            memo=memo,
        )

    async def add_intent_public_key(self, public_key: Optional[str] = None) -> None:
        """
        Register public key for intents.

        Args:
            public_key: Optional public key, defaults to account's public key
        """
        res = await self._account.function_call(
            self.intents_contract,
            "add_public_key",
            {"public_key": self._get_public_key(public_key)},
            MAX_GAS,
            1,
            included=True,
        )
        logger.info(res)

    async def remove_intent_public_key(self, public_key: Optional[str] = None) -> None:
        """
        Remove public key from intents.

        Args:
            public_key: Optional public key, defaults to account's public key
        """
        res = await self._account.function_call(
            self.intents_contract,
            "remove_public_key",
            {"public_key": self._get_public_key(public_key)},
            MAX_GAS,
            1,
            included=True,
        )
        logger.info(res)

    async def simulate_intent(
        self, commitment: Union[Commitment, dict]
    ) -> SimulationResult:
        """
        Simulate intent execution.

        Args:
            commitment: Commitment object or dict

        Returns:
            Simulation result

        Raises:
            SimulationError: If simulation fails
        """
        try:
            res = await self._account.view_function(
                self.intents_contract,
                "simulate_intents",
                {"signed": [self._to_commitment_dict(commitment)]},
            )
            return SimulationResult(**res.result)
        except (InternalError, ViewFunctionError) as e:
            return SimulationResult(error_msg=str(e))

    async def publish_intents(
        self,
        signed_intents: Union[Commitment, dict, List[Commitment], List[dict]],
        quote_hashes: Optional[List[str]] = None,
        wait_for_settlement: bool = False,
    ) -> str:
        """
        Publish intent to solver.

        Args:
            signed_intents: Commitment object or list if Commitments
            quote_hashes: Optional list of quote hashes
            wait_for_settlement: Wait for settlement onchain and return transaction hash

        Returns:
            Response intent hash or transaction hash if wait_for_settlement is True
        """
        # publish_intents
        if isinstance(signed_intents, list):
            rpc_request, _ = self._build_rpc_request(
                "publish_intents",
                [
                    dict(
                        quote_hashes=quote_hashes,
                        signed_datas=[
                            self._to_commitment_dict(c) for c in signed_intents
                        ],
                    )
                ],
            )
        else:
            rpc_request, _ = self._build_rpc_request(
                "publish_intent",
                [
                    dict(
                        quote_hashes=quote_hashes,
                        signed_data=self._to_commitment_dict(signed_intents),
                    )
                ],
            )
        async with self._session.post(
            self.solver_bus_url, json=rpc_request
        ) as response:
            resp = await response.json()
            if resp["result"]["status"] == "OK":
                if "intent_hash" in resp["result"]:
                    intent_hash = resp["result"]["intent_hash"]
                    if wait_for_settlement:
                        return await self.get_tr_hash_from_intent(intent_hash)
                    return intent_hash
                if "intent_hashes" in resp["result"]:
                    intent_hashes = resp["result"]["intent_hashes"]
                    if wait_for_settlement and intent_hashes:
                        return await self.get_tr_hash_from_intent(intent_hashes[0])
                    return intent_hashes
            raise SimulationError(message=resp["result"]["reason"])

    async def get_tr_hash_from_intent(
        self, intent_hash: str, timeout: int = 20
    ) -> Optional[str]:
        """
        Get transaction hash from intent hash.

        Args:
            intent_hash: Intent hash
            timeout: Timeout in seconds

        Returns:
            Transaction hash or None if failed
        """
        for _ in range(timeout // 2):
            rpc_request, headers = self._build_rpc_request(
                "get_status", [{"intent_hash": intent_hash}], headers=True
            )
            async with self._session.post(
                self.solver_bus_url, json=rpc_request, headers=headers
            ) as response:
                intent = await response.json()
                status = intent["result"]["status"]
                if status == "PENDING":
                    await asyncio.sleep(2)
                    continue
                elif status == "SETTLED":
                    return intent["result"]["data"]["hash"]
                else:
                    logger.error(f"Intent {intent_hash} failed with status {status}")
                    return None
        return None

    async def is_nonce_used(self, nonce: str, account_id: Optional[str] = None) -> bool:
        """
        Check if nonce has been used.

        Args:
            nonce: Nonce to check
            account_id: Optional account ID, defaults to self.account_id

        Returns:
            True if nonce is used, False otherwise
        """
        if account_id is None:
            account_id = self.account_id
        is_nonce_used = await self._account.view_function(
            INTENTS_CONTRACT,
            "is_nonce_used",
            {"nonce": nonce, "account_id": account_id},
        )
        return is_nonce_used.result
