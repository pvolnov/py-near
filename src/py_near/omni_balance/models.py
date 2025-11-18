"""Data models for omni_balance operations."""

import datetime
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, field_validator

from loguru import logger

from py_near.omni_balance.constants import INTENTS_CONTRACT


class IntentTypeEnum(str, Enum):
    """Enum for intent types."""

    TOKEN_DIFF = "token_diff"
    TRANSFER = "transfer"
    ADD_PUBLIC_KEY = "add_public_key"
    AUTH_CALL = "auth_call"
    MT_WITHDRAW = "mt_withdraw"
    FT_WITHDRAW = "ft_withdraw"
    NFT_WITHDRAW = "nft_withdraw"
    NATIVE_WITHDRAW = "native_withdraw"


class IntentTokenDiff(BaseModel):
    """Intent for token difference operations."""

    intent: IntentTypeEnum = IntentTypeEnum.TOKEN_DIFF
    diff: Dict[str, str]
    referral: Optional[str] = None


class IntentTransfer(BaseModel):
    """Intent for token transfer operations."""

    intent: IntentTypeEnum = IntentTypeEnum.TRANSFER
    receiver_id: str
    tokens: Dict[str, str]
    memo: Optional[str] = None


class IntentAddKey(BaseModel):
    """Intent for adding public key."""

    intent: IntentTypeEnum = IntentTypeEnum.ADD_PUBLIC_KEY
    public_key: str


class IntentAuthCallback(BaseModel):
    """Intent for authentication callback."""

    intent: IntentTypeEnum = IntentTypeEnum.AUTH_CALL
    contract_id: str
    msg: str
    attached_deposit: str = "0"
    min_gas: Optional[str] = None


class IntentMtWithdraw(BaseModel):
    """Intent for multi-token withdrawal."""

    intent: IntentTypeEnum = IntentTypeEnum.MT_WITHDRAW
    token: str
    receiver_id: str
    token_ids: List[str]
    amounts: List[str]
    memo: Optional[str] = None
    msg: Optional[str] = None


class IntentFtWithdraw(BaseModel):
    """Intent for fungible token withdrawal."""

    intent: IntentTypeEnum = IntentTypeEnum.FT_WITHDRAW
    token: str
    receiver_id: str
    amount: str
    memo: Optional[str] = None
    msg: Optional[str] = None


class IntentNftWithdraw(BaseModel):
    """Intent for NFT withdrawal."""

    intent: IntentTypeEnum = IntentTypeEnum.NFT_WITHDRAW
    token: str
    token_id: str
    receiver_id: str
    memo: Optional[str] = None
    msg: Optional[str] = None


class NativeWithdraw(BaseModel):
    """Intent for native NEAR withdrawal."""

    intent: IntentTypeEnum = IntentTypeEnum.NATIVE_WITHDRAW
    receiver_id: str
    amount: str
    memo: Optional[str] = None


IntentType = Union[
    IntentTokenDiff,
    IntentTransfer,
    IntentMtWithdraw,
    IntentFtWithdraw,
    IntentAddKey,
    IntentAuthCallback,
    IntentNftWithdraw,
    NativeWithdraw,
]


class IntentAction(BaseModel):
    """Base intent action model."""

    signer_id: str
    deadline: str
    intents: List[IntentType]


class Quote(IntentAction):
    """Quote model with nonce and verifying contract."""

    nonce: str
    verifying_contract: Optional[str] = INTENTS_CONTRACT


class NEP413PayloadRaw(BaseModel):
    """NEP-413 payload raw structure."""

    message: str
    nonce: str
    recipient: str


class Erc191PayloadMassage(BaseModel):
    """ERC-191 payload message structure."""

    signer_id: str
    deadline: str
    intents: List[IntentType]


class NEP413Payload(BaseModel):
    """NEP-413 payload model."""

    message: Union[IntentAction, str]
    nonce: str
    recipient: str

    @field_validator("message", mode="before")
    def parse_message(cls, v):
        """Parse message from string or dict."""
        if isinstance(v, str):
            return IntentAction(**json.loads(v))
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with JSON string message."""
        res = super().model_dump()
        res["message"] = self.message.model_dump_json()
        logger.info("to_dict", res)
        return res

    def model_dump_json(self, *args, **kargs) -> str:
        """Dump to JSON string."""
        return json.dumps(self.to_dict())


class RawPayload(BaseModel):
    """Raw payload model."""

    nonce: str
    signer_id: str
    deadline: str
    intents: List[IntentType]
    verifying_contract: Optional[str] = None

    def to_dict(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json()


class TonPayload(BaseModel):
    """TON Connect payload model."""

    text: RawPayload
    type: str

    @field_validator("text", mode="before")
    def parse_message(cls, v):
        """Parse text from string or dict."""
        if isinstance(v, str):
            return RawPayload(**json.loads(v))
        return v


class WebAuthnPayload(BaseModel):
    """WebAuthn payload model."""

    deadline: str
    nonce: str
    verifying_contract: str
    signer_id: str
    intents: List[IntentType]


class Erc191Payload(RawPayload):
    """ERC-191 payload model."""

    pass


class Commitment(BaseModel):
    """Commitment model for signed intents."""

    payload: Any
    public_key: Optional[str] = None
    timestamp: Optional[int] = None
    address: Optional[str] = None
    domain: Optional[str] = None
    signature: str
    standard: str
    authenticator_data: Optional[str] = None
    client_data_json: Optional[str] = None

    @property
    def payload_structure(
        self,
    ) -> Union[NEP413Payload, RawPayload, Erc191Payload, TonPayload, WebAuthnPayload]:
        """Get parsed payload structure based on standard."""
        models: Dict[str, Type[BaseModel]] = {
            "nep413": NEP413Payload,
            "raw_ed25519": RawPayload,
            "erc191": RawPayload,
            "sep53": RawPayload,
            "ton_connect": TonPayload,
            "webauthn": WebAuthnPayload,
        }

        if self.standard not in models:
            raise ValueError(f"Unsupported standard: {self.standard}")

        payload = self.payload
        if isinstance(payload, str):
            payload = json.loads(payload)

        return models[self.standard](**payload)

    def _get_payload_attr(self, attr: str, ton_attr: str = None, nep_attr: str = None):
        """Helper to extract attribute from payload structure."""
        ps = self.payload_structure
        if isinstance(ps, TonPayload):
            return getattr(ps.text, ton_attr or attr)
        if isinstance(ps, NEP413Payload):
            return getattr(ps.message, nep_attr or attr)
        if isinstance(ps, (RawPayload, Erc191Payload, WebAuthnPayload)):
            return getattr(ps, attr)
        raise ValueError("Unknown payload type")

    @property
    def intents(self) -> List[IntentType]:
        """Extract intents from payload structure."""
        return self._get_payload_attr("intents")

    @property
    def signer_id(self) -> str:
        """Extract signer ID from payload structure."""
        return self._get_payload_attr("signer_id")

    @property
    def nonce(self):
        """Extract nonce from payload structure."""
        return self._get_payload_attr("nonce")

    @property
    def deadline_ts(self) -> int:
        """Get deadline as timestamp."""
        deadline_str = self._get_payload_attr("deadline")
        return int(datetime.datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())

    @property
    def deadline(self) -> str:
        """Get deadline as string."""
        return self._get_payload_attr("deadline")

    def to_dict(self):
        """Convert to dictionary, removing None values."""
        res = super().model_dump()
        for key in ["timestamp", "address", "domain", "authenticator_data", "client_data_json"]:
            if not res.get(key):
                del res[key]
        return res


class PublishIntent(BaseModel):
    """Model for publishing a single intent."""

    signed_data: Union[Commitment, dict]
    quote_hashes: List[str]


class PublishIntents(BaseModel):
    """Model for publishing multiple intents."""

    signed_datas: List[Commitment]
    quote_hashes: List[str]


class IntentMultiQuotesOutModel(BaseModel):
    """Model for multi-quote output."""

    quote_hashes: List[str]
    amount_out: str
    quote: Quote
    signed_fee_quote: Optional[Commitment] = None
    fees: Optional[str] = None
    logs: Optional[List[str]] = None


class IntentQuotesExactOutModel(BaseModel):
    """Model for exact output quotes."""

    quote_hashes: List[str]
    amount_in: str
    signed_fee_quote: Optional[Commitment] = None
    fees: Optional[str] = None
    logs: Optional[List[str]] = None


@dataclass
class QuoteHashOutModel:
    """
    Model representing token swap quote result.

    Attributes:
        quote_hashes: List of quote hashes
        amount_out: Output token amount
        amount_in: Input token amount
        token_in: Input token identifier
        token_out: Output token identifier
    """

    quote_hashes: List[str]
    amount_out: str
    amount_in: str
    token_in: str
    token_out: str


class IntentExecuted(BaseModel):
    """Model for executed intent information."""

    intent_hash: str
    account_id: str
    nonce: str


class SimulationState(BaseModel):
    """Model for simulation state."""

    fee: int
    current_salt: str


class SimulationResult(BaseModel):
    """Model for intent simulation result."""

    error_msg: Optional[str] = None
    intents_executed: List[IntentExecuted] = []
    logs: List[str] = []
    min_deadline: Optional[str] = None
    state: Optional[SimulationState] = None

    @property
    def success(self) -> bool:
        """Check if simulation was successful."""
        return self.error_msg is None

    @property
    def min_deadline_ts(self) -> int:
        """Get minimum deadline as timestamp."""
        if not self.min_deadline:
            return 0
        return int(datetime.datetime.strptime(self.min_deadline, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())

    @property
    def logged_intents(self) -> List[IntentType]:
        """
        Extract executed intents from logs.

        Parses EVENT_JSON logs and reconstructs IntentType objects.

        Returns:
            List of IntentType objects extracted from logs
        """
        intents = []
        event_type_to_intent_class = {
            "transfer": IntentTransfer,
            "token_diff": IntentTokenDiff,
            "add_public_key": IntentAddKey,
            "auth_call": IntentAuthCallback,
            "mt_withdraw": IntentMtWithdraw,
            "ft_withdraw": IntentFtWithdraw,
            "nft_withdraw": IntentNftWithdraw,
            "native_withdraw": NativeWithdraw,
        }

        for log in self.logs:
            if not log.startswith("EVENT_JSON:"):
                continue

            try:
                json_str = log[len("EVENT_JSON:") :]
                event_data = json.loads(json_str)
                event_type = event_data.get("event")

                if event_type not in event_type_to_intent_class:
                    continue

                intent_class = event_type_to_intent_class[event_type]
                data_list = event_data.get("data", [])

                for data_item in data_list:
                    intent_data = dict()
                    if event_type == "transfer":
                        intent_data = {
                            "receiver_id": data_item.get("receiver_id"),
                            "tokens": data_item.get("tokens", dict()),
                            "memo": data_item.get("memo"),
                        }
                    elif event_type == "token_diff":
                        intent_data = {
                            "diff": data_item.get("diff", dict()),
                            "referral": data_item.get("referral"),
                        }
                    elif event_type == "add_public_key":
                        intent_data = {"public_key": data_item.get("public_key")}
                    elif event_type == "auth_call":
                        intent_data = {
                            "contract_id": data_item.get("contract_id"),
                            "msg": data_item.get("msg"),
                            "attached_deposit": data_item.get("attached_deposit", "0"),
                            "min_gas": data_item.get("min_gas"),
                        }
                    elif event_type == "mt_withdraw":
                        intent_data = {
                            "token": data_item.get("token"),
                            "receiver_id": data_item.get("receiver_id"),
                            "token_ids": data_item.get("token_ids", []),
                            "amounts": data_item.get("amounts", []),
                            "memo": data_item.get("memo"),
                            "msg": data_item.get("msg"),
                        }
                    elif event_type == "ft_withdraw":
                        intent_data = {
                            "token": data_item.get("token"),
                            "receiver_id": data_item.get("receiver_id"),
                            "amount": data_item.get("amount"),
                            "memo": data_item.get("memo"),
                            "msg": data_item.get("msg"),
                        }
                    elif event_type == "nft_withdraw":
                        intent_data = {
                            "token": data_item.get("token"),
                            "token_id": data_item.get("token_id"),
                            "receiver_id": data_item.get("receiver_id"),
                            "memo": data_item.get("memo"),
                            "msg": data_item.get("msg"),
                        }
                    elif event_type == "native_withdraw":
                        intent_data = {
                            "receiver_id": data_item.get("receiver_id"),
                            "amount": data_item.get("amount"),
                            "memo": data_item.get("memo"),
                        }

                    intent_data = {k: v for k, v in intent_data.items() if v is not None}
                    try:
                        intent = intent_class(**intent_data)
                        intents.append(intent)
                    except Exception as e:
                        logger.warning(f"Failed to parse intent from log: {e}")

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse log entry: {log[:100]}, error: {e}")
                continue

        return intents

